import heapq
import pandas as pd
from datetime import datetime, timedelta
class Vehicle:
    def __init__(self, vid, vtype, entry_time):
        self.vid = vid
        self.vtype = vtype
        self.entry_time = entry_time
        self.is_priority = self.is_priority_vehicle()
        self.time_cost = 30 if self.is_priority else (90 if vtype in ['private', 'commercial_rental'] else 180)
    def is_priority_vehicle(self):
        return self.vid.upper().startswith(("VIP", "EMS", "POLICE", "AMB")) or self.vtype == 'priority'
class TollBoothSystem:
    def __init__(self, num_tolls, num_lanes, max_queue_size):
        self.num_tolls = num_tolls
        self.num_lanes = num_lanes
        self.max_queue_size = max_queue_size
        self.graph = {}
        self.lane_to_tolls = {}
        self.nodes = set()
        self.lane_status = {f"L{i}": [] for i in range(1, num_lanes + 1)}  
        self.toll_status = {f"T{i}": {'count': 0, 'end_time': datetime.min} for i in range(1, num_tolls + 1)}  
    def input_lane_connections(self):
        for i in range(1, self.num_lanes + 1):
            lane = f"L{i}"
            tolls = input(f"Enter tolls connected to {lane} : ").split(',')
            self.lane_to_tolls[lane] = [t.strip() for t in tolls if t.strip()]
            self.nodes.add(lane)
            for t in self.lane_to_tolls[lane]:
                self.nodes.add(t)
        self.nodes.add("E")
    def build_weighted_graph(self, vehicle):
        weights = {node: {} for node in self.nodes}
        vtime = vehicle.time_cost
        for lane, tolls in self.lane_to_tolls.items():
            penalty_lane = len(self.lane_status[lane]) * (5 if vehicle.is_priority else 10)
            for toll in tolls:
                penalty_toll = self.toll_status[toll]['count'] * 5
                weights[lane][toll] = vtime + penalty_lane + penalty_toll
        for i in range(1, self.num_tolls + 1):
            toll = f"T{i}"
            weights[toll]["E"] = vtime + self.toll_status[toll]['count'] * 5
        weights["E"] = {}
        return weights
    def dijkstra(self, weights, start):
        min_time = {node: float('inf') for node in weights}
        min_time[start] = 0
        prev = {}
        queue = [(0, start)]
        while queue:
            curr_time, node = heapq.heappop(queue)
            for neighbor, wt in weights.get(node, {}).items():
                time = curr_time + wt
                if time < min_time[neighbor]:
                    min_time[neighbor] = time
                    prev[neighbor] = node
                    heapq.heappush(queue, (time, neighbor))
        return min_time, prev
    def get_shortest_path(self, prev, end="E"):
        path = []
        while end in prev:
            path.append(end)
            end = prev[end]
        path.append(end)
        return path[::-1]
    def reallocate_non_priority_vehicles(self, lane):
        new_queue = []
        for vehicle in self.lane_status[lane]:
            if vehicle.is_priority:
                new_queue.append(vehicle)
            else:
                best_path, new_lane = self.find_best_path(vehicle, exclude_lane=lane)
                if new_path := best_path:
                    self.lane_status[new_lane].append(vehicle)
                    for node in best_path:
                        if node.startswith("T"):
                            self.toll_status[node]['count'] += 1
                    exit_time = vehicle.entry_time + timedelta(seconds=vehicle.time_cost)
                    self.save_vehicle_data(vehicle, new_lane, vehicle.entry_time, exit_time, best_path)
                else:
                    new_queue.append(vehicle)  
        self.lane_status[lane] = new_queue
    def find_best_path(self, vehicle, exclude_lane=None):
        weights = self.build_weighted_graph(vehicle)
        best_path = None
        min_time = float('inf')
        best_lane = None
        for lane in self.lane_to_tolls:
            if lane == exclude_lane:
                continue
            times, prev = self.dijkstra(weights, lane)
            if times["E"] < min_time:
                min_time = times["E"]
                best_path = self.get_shortest_path(prev)
                best_lane = lane
        return best_path, best_lane
    def assign_path(self, vehicle):
        if vehicle.is_priority:
            print(f"Priority vehicle detected: {vehicle.vid} — clearing lanes...")
            for lane in self.lane_status:
                if any(v.is_priority for v in self.lane_status[lane]):
                    self.reallocate_non_priority_vehicles(lane)
        best_path, assigned_lane = self.find_best_path(vehicle)
        if best_path:
            for toll in best_path:
                if toll.startswith("T"):
                    toll_end_time = self.toll_status[toll]['end_time']
                    if vehicle.entry_time < toll_end_time:
                        print(f"Toll {toll} is still occupied. Vehicle {vehicle.vid} cannot be assigned.")
                        return
            self.lane_status[assigned_lane].append(vehicle)
            for node in best_path:
                if node.startswith("T"):
                    self.toll_status[node]['count'] += 1
                    toll_end_time = vehicle.entry_time + timedelta(seconds=vehicle.time_cost)
                    self.toll_status[node]['end_time'] = max(self.toll_status[node]['end_time'], toll_end_time)
            exit_time = vehicle.entry_time + timedelta(seconds=vehicle.time_cost)
            print(f"\nVehicle {vehicle.vid} ({vehicle.vtype}) assigned path: {' → '.join(best_path)}")
            print(f"Total time: {vehicle.time_cost} seconds")
            print(f" Entry time: {vehicle.entry_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Exit time: {exit_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            print("Lane Status:")
            for lane, vlist in self.lane_status.items():
                print(f"  {lane}: {len(vlist)}  vehicle(s)")
            print("Toll Status:")
            for toll, status in self.toll_status.items():
                print(f" {toll}: {status['count']} vehicle(s)")
            self.save_vehicle_data(vehicle, assigned_lane, vehicle.entry_time, exit_time, best_path)
        else:
            print(f"No valid path found for vehicle {vehicle.vid}.\n")
    def save_vehicle_data(self, vehicle, lane, entry_time, exit_time, path):
        vehicle_data = {
            "Vehicle ID": vehicle.vid,
            "Vehicle Type": vehicle.vtype,
            "Is Priority": "Yes" if vehicle.is_priority else "No",
            "Assigned Lane": lane,
            "Toll Path": " → ".join(path[1:-1]),
            "Entry Time": entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            "Exit Time": exit_time.strftime('%Y-%m-%d %H:%M:%S'),
            "Total Time (s)": int((exit_time - entry_time).total_seconds())
        }
        try:
            df = pd.read_excel("vehicle_data13.xlsx")
            df = pd.concat([df, pd.DataFrame([vehicle_data])], ignore_index=True)
        except FileNotFoundError:
            df = pd.DataFrame([vehicle_data])
        df.to_excel("vehicle_data13.xlsx", index=False)
def main():
    print("Toll Booth Optimizer")
    try:
        tolls = int(input("Enter number of tolls: "))
        lanes = int(input("Enter number of lanes: "))
        queuesize = int(input("Enter max queue size per lane: "))
    except ValueError:
        print("Invalid input. Please enter valid integers.")
        return
    system = TollBoothSystem(tolls, lanes, queuesize)
    system.input_lane_connections()
    while True:
        print("\n1. Add vehicle")
        print("2. Exit")
        choice = input("Enter choice: ")
        if choice == '1':
            vid = input("Enter Vehicle Number/ID: ").strip().upper()
            entry_time = datetime.now()
            print("Vehicle Types: private, public, commercial_rental, commercial_transport, priority, vip")
            vtype = input("Enter Vehicle Type: ").strip().lower()
            if vtype not in ['private', 'public', 'commercial_rental', 'commercial_transport', 'priority', 'vip']:
                print("Invalid vehicle type. Try again.")
                continue
            if vtype in ['priority', 'vip']:
                vtype = 'priority'  
            vehicle = Vehicle(vid, vtype, entry_time)
            system.assign_path(vehicle)
        elif choice == '2':
            print("Exiting Toll Booth System. Goodbye!")
            break
        else:
            print("Invalid choice. Please select again.")
if __name__ == "__main__":
    main()
