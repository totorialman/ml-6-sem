import simpy
import random
from collections import defaultdict

L = 50 
K = 40  
S = 30  

SIM_TIME = 2160  # 3 месяца в часах
MAINTENANCE_TYPES = ['A', 'B', 'C']

# Время безотказной работы
TA_RANGE = (420, 520)
TB_RANGE = (460, 560)
TC_RANGE = (520, 560)

# Время ремонта
QA_RANGE = (3, 9)
QB_RANGE = (4, 8)
QC_RANGE = (2, 7)

# График работы мастеров
WORK_HOURS = 12
REST_HOURS = 36
CYCLE_HOURS = WORK_HOURS + REST_HOURS

MASTER_ASSIGNMENT = {
    0: 'A',
    1: 'B',
    2: 'C',
    3: 'A'  
}

stats = {
    "repaired": defaultdict(int),
    "downtime": defaultdict(float),
    "busy_time": defaultdict(float),
    "total_masters": len(MASTER_ASSIGNMENT)
}


def time_between_failure(computer_type):
    if computer_type == 'A':
        return random.uniform(*TA_RANGE)
    elif computer_type == 'B':
        return random.uniform(*TB_RANGE)
    else:
        return random.uniform(*TC_RANGE)


def repair_duration(computer_type):
    if computer_type == 'A':
        return random.uniform(*QA_RANGE)
    elif computer_type == 'B':
        return random.uniform(*QB_RANGE)
    else:
        return random.uniform(*QC_RANGE)


class Master:
    def __init__(self, env, master_id, comp_type):
        self.env = env
        self.master_id = master_id
        self.comp_type = comp_type
        self.resource = simpy.Resource(env, capacity=1)
        self.total_busy_time = 0

    def work(self, computer):
        with self.resource.request() as req:
            yield req
            start = self.env.now
            print(f"{self.env.now:.2f}: Компьютер {computer.id} типа {computer.comp_type} начал ремонт у мастера {self.master_id}")
            repair_time = repair_duration(computer.comp_type)
            yield self.env.timeout(repair_time)
            stats["repaired"][self.comp_type] += 1
            downtime = self.env.now - computer.broken_at
            stats["downtime"][self.comp_type] += downtime
            self.total_busy_time += self.env.now - start
            stats["busy_time"][self.master_id] = self.total_busy_time
            print(f"{self.env.now:.2f}: Компьютер {computer.id} типа {computer.comp_type} отремонтирован мастером {self.master_id}, простой: {downtime:.2f} ч")


def master_schedule(env, master):
    while True:
        available_time = (env.now % CYCLE_HOURS)
        if available_time < WORK_HOURS:
            yield env.timeout(WORK_HOURS - available_time)
        else:
            yield env.timeout(CYCLE_HOURS - available_time)

        yield env.timeout(REST_HOURS)


class Computer:
    def __init__(self, env, comp_id, comp_type):
        self.env = env
        self.id = comp_id
        self.comp_type = comp_type
        self.broken_at = None
        self.process = env.process(self.run())

    def run(self):
        while True:
            time_to_break = time_between_failure(self.comp_type)
            try:
                yield self.env.timeout(time_to_break)
                print(f"{self.env.now:.2f}: Компьютер {self.id} типа {self.comp_type} сломался")
                self.broken_at = self.env.now

                for master in masters_by_type[self.comp_type]:
                    if master.resource.count == 0:
                        repair_process = env.process(master.work(self))
                        yield repair_process
                        break
                else:
                    for master in masters_by_type[self.comp_type]:
                        yield env.process(master.work(self))
                        break

            except simpy.Interrupt:
                pass


env = simpy.Environment()

masters = []
masters_by_type = {t: [] for t in MAINTENANCE_TYPES}
for mid, mtype in MASTER_ASSIGNMENT.items():
    master = Master(env, mid, mtype)
    masters.append(master)
    masters_by_type[master.comp_type].append(master)

for master in masters:
    env.process(master_schedule(env, master))

computers = []
for i in range(L):
    computers.append(Computer(env, f"A{i+1}", 'A'))
for i in range(K):
    computers.append(Computer(env, f"B{i+1}", 'B'))
for i in range(S):
    computers.append(Computer(env, f"C{i+1}", 'C'))

env.run(until=SIM_TIME)

print("\nСтатистика:")
for mid in MASTER_ASSIGNMENT:
    comp_type = MASTER_ASSIGNMENT[mid]
    busy_time = stats['busy_time'].get(mid, 0)
    percent_busy = busy_time / SIM_TIME * 100
    print(f"Мастер {mid} (тип {comp_type}): занят {busy_time:.2f} ч  ({percent_busy:.2f}%)")

print("\nКоличество отремонтированных компьютеров:")
for typ in MAINTENANCE_TYPES:
    print(f"Тип {typ}: {stats['repaired'][typ]}")
print("\nСреднее время простоя одного компьютера:")
for typ in MAINTENANCE_TYPES:
    count = stats['repaired'][typ]
    total_downtime = stats['downtime'][typ]
    avg_downtime = total_downtime / count if count > 0 else 0
    print(f"Тип {typ}: {avg_downtime:.2f} ч")
