import threading
import os
import sys
import subprocess
import random
import numpy as np
import keras
import datetime
import h5py
print("      1          ")
from collections import deque
from keras.layers import Input, Conv2D, Flatten, Dense
from keras.models import Model
print("  3")
from aux import DQNAgent_tri
from aux import SumoTrisection
print("         b")

try:
    sys.path.append(os.path.join(os.path.dirname(
        __file__), '..', '..', '..', '..', "tools"))  # tutorial in tests
    sys.path.append(os.path.join(os.environ.get("SUMO_HOME", os.path.join(
        os.path.dirname(__file__), "..", "..", "..")), "tools"))  # tutorial in docs
    from sumolib import checkBinary
except ImportError:
    sys.exit(
        "please declare environment variable 'SUMO_HOME' as the root directory of your sumo installation (it should contain folders 'bin', 'tools' and 'docs')")
PORT = 8873
import traci
print("\n     2     ")
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ln8 = ["R37","R33","R8","R39"]
ln7 = ["R32","R30","R36","R34"]
ln12 = ["R48","R49","R46","R43"]
ln9 = ["R38","R42","R44"]
ln10 = ["R31","R50","R91"]
class DQNAgent:
    def __init__(self):
        self.gamma = 0.95   # discount rate
        self.epsilon = 0.1  # exploration rate
        self.learning_rate = 0.0002
        self.memory = deque(maxlen=200)
        self.model = self._build_model()
        self.action_size = 2

    def _build_model(self):
        # Neural Net for Deep-Q learning Model
        input_1 = Input(shape=(12, 12, 1))
        x1 = Conv2D(16, (4, 4), strides=(2, 2), activation='relu')(input_1)
        x1 = Conv2D(32, (2, 2), strides=(1, 1), activation='relu')(x1)
        x1 = Flatten()(x1)

        input_2 = Input(shape=(12, 12, 1))
        x2 = Conv2D(16, (4, 4), strides=(2, 2), activation='relu')(input_2)
        x2 = Conv2D(32, (2, 2), strides=(1, 1), activation='relu')(x2)
        x2 = Flatten()(x2)

        input_3 = Input(shape=(2, 1))
        x3 = Flatten()(input_3)

        x = keras.layers.concatenate([x1, x2, x3])
        x = Dense(128, activation='relu')(x)
        x = Dense(64, activation='relu')(x)
        x = Dense(2, activation='linear')(x)

        model = Model(inputs=[input_1, input_2, input_3], outputs=[x])
        model.compile(optimizer=keras.optimizers.RMSprop(
            lr=self.learning_rate), loss='mse')

        return model

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        act_values = self.model.predict(state)

        return np.argmax(act_values[0])  # returns action

    def replay(self, batch_size):
        minibatch = random.sample(self.memory, batch_size)
        for state, action, reward, next_state, done in minibatch:
            target = reward
            if not done:
                target = (reward + self.gamma *
                          np.amax(self.model.predict(next_state)[0]))
            target_f = self.model.predict(state)
            target_f[0][action] = target
            self.model.fit(state, target_f, epochs=1, verbose=0)

    def load(self, name):
        self.model.load_weights(name)

    def save(self, name):
        self.model.save_weights(name)


class SumoIntersection:
    def __init__(self, junction, lanes):
        self.junction = junction
        self.lanes = lanes

    def getState(self):
        positionMatrix = []
        velocityMatrix = []

        cellLength = 7
        offset = 11
        speedLimit = 14

        junctionPosition = traci.junction.getPosition(str(self.junction))[0]
        vehicles_road1 = traci.edge.getLastStepVehicleIDs(str(self.lanes[0]))
        vehicles_road2 = traci.edge.getLastStepVehicleIDs(str(self.lanes[1]))
        vehicles_road3 = traci.edge.getLastStepVehicleIDs(str(self.lanes[2]))
        vehicles_road4 = traci.edge.getLastStepVehicleIDs(str(self.lanes[3]))
        for i in range(12):
            positionMatrix.append([])
            velocityMatrix.append([])
            for j in range(12):
                positionMatrix[i].append(0)
                velocityMatrix[i].append(0)

        for v in vehicles_road1:
            ind = int(
                abs((junctionPosition - traci.vehicle.getPosition(v)[0] - offset)) / cellLength)
            if(ind < 12):
                positionMatrix[2 - traci.vehicle.getLaneIndex(v)][11 - ind] = 1
                velocityMatrix[2 - traci.vehicle.getLaneIndex(
                    v)][11 - ind] = traci.vehicle.getSpeed(v) / speedLimit

        for v in vehicles_road2:
            ind = int(
                abs((junctionPosition - traci.vehicle.getPosition(v)[0] + offset)) / cellLength)
            if(ind < 12):
                positionMatrix[3 + traci.vehicle.getLaneIndex(v)][ind] = 1
                velocityMatrix[3 + traci.vehicle.getLaneIndex(
                    v)][ind] = traci.vehicle.getSpeed(v) / speedLimit

        junctionPosition = traci.junction.getPosition(str(self.junction))[1]
        for v in vehicles_road3:
            ind = int(
                abs((junctionPosition - traci.vehicle.getPosition(v)[1] - offset)) / cellLength)
            if(ind < 12):
                positionMatrix[6 + 2 -
                               traci.vehicle.getLaneIndex(v)][11 - ind] = 1
                velocityMatrix[6 + 2 - traci.vehicle.getLaneIndex(
                    v)][11 - ind] = traci.vehicle.getSpeed(v) / speedLimit

        for v in vehicles_road4:
            ind = int(
                abs((junctionPosition - traci.vehicle.getPosition(v)[1] + offset)) / cellLength)
            if(ind < 12):
                positionMatrix[9 + traci.vehicle.getLaneIndex(v)][ind] = 1
                velocityMatrix[9 + traci.vehicle.getLaneIndex(
                    v)][ind] = traci.vehicle.getSpeed(v) / speedLimit

        light = [0, 1]

        position = np.array(positionMatrix)
        position = position.reshape(1, 12, 12, 1)

        velocity = np.array(velocityMatrix)
        velocity = velocity.reshape(1, 12, 12, 1)

        lgts = np.array(light)
        lgts = lgts.reshape(1, 2, 1)

        return [position, velocity, lgts]


    def calculateReward(self, wgMatrix):
        reward = 0
        r1 = 0
        r2 = 0
        r3 = 0
        r4 = 0
        vehicles_road1 = traci.edge.getLastStepVehicleIDs(str(self.lanes[0]))
        vehicles_road2 = traci.edge.getLastStepVehicleIDs(str(self.lanes[1]))
        vehicles_road3 = traci.edge.getLastStepVehicleIDs(str(self.lanes[2]))
        vehicles_road4 = traci.edge.getLastStepVehicleIDs(str(self.lanes[3]))

        for v in vehicles_road1:
            if (len(weight_matrix) != 0 and v in wgMatrix):
                 #reward += wgMatrix[v]
                reward += (wgMatrix[v]*traci.vehicle.getWaitingTime(self,v))
                r4 += wgMatrix[v]

            else:
                reward = reward + 1
                r4 = r4 + 1

        for v in vehicles_road2:
            if (len(weight_matrix) != 0 and v in wgMatrix):
                #reward += wgMatrix[v]
                reward += (wgMatrix[v]*traci.vehicle.getWaitingTime(self,v))
                r3 += wgMatrix[v]
            else:
                reward = reward + 1
                r3 = r3 + 1

        for v in vehicles_road3:
            if (len(weight_matrix) != 0 and v in wgMatrix):
                #reward += wgMatrix[v]
                reward += (wgMatrix[v]*traci.vehicle.getWaitingTime(self,v))
                r2 += wgMatrix[v]
            else:
                reward = reward + 1
                r2  = r2 + 1


        for v in vehicles_road4:
            if (len(weight_matrix) != 0 and v in wgMatrix):
                #reward += wgMatrix[v]
                reward += (wgMatrix[v]*traci.vehicle.getWaitingTime(self,v))
                r1 += wgMatrix[v]
            else:
                reward = reward + 1
                r1 = r1 + 1


        return [reward, r1, r2, r3, r4]

weight_matrix = []
a = 10
b = 10
c = 10
d = 10
e = 10
sdn = 10
state_7 = list()
state_8 = list()
state_9 = list()
state_10 = list()
state_12 = list()

def sum1(input):
    return sum(map(sum, input))

def generate_signal_n8(agent):
    sumoInt = SumoIntersection("N8",ln8)
    state = sumoInt.getState()
    action = agent.act(state)
    state_8 = sumoInt.getState()
    return action


def generate_signal_n7(agent):
    sumoInt = SumoIntersection("N7",ln7)
    state = sumoInt.getState()
    action = agent.act(state)
    state_7 = sumoInt.getState()
    return action

def generate_signal_n12(agent):
    sumoInt = SumoIntersection("N12",ln12)
    state = sumoInt.getState()
    action = agent.act(state)
    state_12 = sumoInt.getState()
    return action


def generate_signal_n9(agent):
    sumoInt = SumoTrisection("N9",ln9)
    state = sumoInt.getState()
    action = agent.act(state) 
    state_9 = sumoInt.getState()
    return action


def generate_signal_n10(agent):
    sumoInt = SumoTrisection("N10",ln10)
    state = sumoInt.getState()
    action = agent.act(state) 
    state_10 = sumoInt.getState()
    return action


if __name__ == '__main__':
    turn8 = 0
    turn7 = 0
    turn9 = 0
    turn10 = 0
    turn12 = 0
    step8 = 0
    step7 = 0
    step9 = 0
    step10 = 0
    step12 = 0
    step = 0
    agent1 = DQNAgent()
    agent2 = DQNAgent()
    agent3 = DQNAgent_tri()
    agent4 = DQNAgent_tri()
    agent5 = DQNAgent()

    agent1.load('N7.h5')
    agent2.load('N8.h5')
    agent3.load('N9.h5')
    agent4.load('N10.h5')
    agent5.load('N12.h5')
    sumoBinary = checkBinary('sumo-gui')
    sumoProcess = subprocess.Popen([sumoBinary, "-c", "map/gwalior.sumocfg", "--tripinfo-output",
                            "tripinfo.xml","--quit-on-end","true","--start","false", "--remote-port",str(PORT)], stdout=sys.stdout, stderr=sys.stderr)
    traci.init(PORT)
    
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.trafficlight.setPhase('N8',turn8)
        traci.trafficlight.setPhase('N7',turn7)
        traci.trafficlight.setPhase('N9',turn9)
        traci.trafficlight.setPhase('N10',turn10)
        traci.trafficlight.setPhase('N12',turn12)        
        if step8 == a:
            action = generate_signal_n8(agent1)
            if action == 1:
                turn8 = (turn8 + 1) % 4
            step8 = 0
        if step7 == b:
            action = generate_signal_n7(agent2)
            if action == 1:
                turn7 = (turn7 + 1) % 4
            step7 = 0
        if step9 == c:
            action = generate_signal_n9(agent3)
            if action == 1:
                turn9 = (turn9 + 1) % 4
            step9 = 0
        if step10 == b:
            action = generate_signal_n10(agent4)
            if action == 1:
                turn10 = (turn10 + 1) % 4
            step10 = 0
        if step12 == b:
            action = generate_signal_n12(agent5)
            if action == 1:
                turn12 = (turn12 + 1) % 4
            step12 = 0                        
        if step == sdn:
            if sum1(state_8) > sum1(state_7) and sum1(state_8) > sum1(state_9) and sum1(state_8) > sum1(state_10) and sum1(state_8) > sum1(state_12): 
                a = 12
                b = 8
                c = 8
                d = 8
                e = 8
            elif sum1(state_7) > sum1(state_8) and sum1(state_7) > sum1(state_9) and sum1(state_7) > sum1(state_10) and sum1(state_7) > sum1(state_12):
                a = 8
                b = 12
                c = 8
                d = 8
                e = 8 
            elif sum1(state_9) > sum1(state_8) and sum1(state_9) > sum1(state_7) and sum1(state_9) > sum1(state_10) and sum1(state_9) > sum1(state_12):
                a = 8
                b = 8
                c = 12
                d = 8
                e = 8
            elif sum1(state_10) > sum1(state_8) and sum1(state_10) > sum1(state_9) and sum1(state_10) > sum1(state_7) and sum1(state_10) > sum1(state_12):
                a = 8
                b = 8
                c = 8
                d = 12
                e = 8 
            else:
                a = 8
                b = 8
                c = 8
                d = 8
                e = 12
            step = 0    
        traci.simulationStep()
        step += 1
        step8 += 1
        step7 += 1
        step9 += 1
        step10 += 1
        step12 += 1
        
