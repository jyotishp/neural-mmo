from pdb import set_trace as T
from collections import defaultdict

import time
import numpy as np
import ray
import gym

from forge.blade import core
from forge.blade.lib.ray import init
from forge.blade.io.action import static as action

from forge.ethyr.torch import param

import torch
from torch import nn
from torch.distributions import Categorical

def oneHot(i, n):
   vec = [0 for _ in range(n)]
   vec[i] = 1
   return vec

class Config(core.Config):
   NENT    = 256
   NPOP    = 8

   NREALM  = 256
   NWORKER = 96

   EMBED   = 32
   HIDDEN  = 32
   WINDOW  = 4

   OPTIM_STEPS = 1024
   RENDER      = False

   ENV         = 'NeuralMMO-v1.3'
   OPTIM_STEPS = 128
   CONTINUOUS  = False
   INPUT_DIM   = 492
   OUTPUT_DIM  = 4
   NOISE_STD   = 0.1
   LR          = 0.01

   '''
   ENV         = 'CartPole-v0'
   CONTINUOUS  = False
   INPUT_DIM   = 4
   OUTPUT_DIM  = 2
   NOISE_STD   = 0.1
   LR          = 0.01
   '''

   #ENV         = 'BipedalWalker-v3'
   #CONTINUOUS  = True
   #INPUT_DIM   = 24
   #OUTPUT_DIM  = 4
   #NOISE_STD   = 0.01
   #LR          = 0.01

   #ENV         = 'MountainCarContinuous-v0'
   #CONTINUOUS  = True
   #INPUT_DIM   = 2
   #OUTPUT_DIM  = 1
   #NOISE_STD   = 0.01
   #LR          = 0.01

class Policy(nn.Module):
   def __init__(self, config, xDim, yDim, recur=False):
      super().__init__()
      self.recur = recur
      if recur:
         self.hidden  = nn.LSTM(config.EMBED, config.HIDDEN, batch_first=True)
      else:  
         self.hidden = nn.Linear(config.EMBED, config.HIDDEN)

      self.embed  = nn.Linear(xDim, config.EMBED)
      self.action = nn.Linear(config.HIDDEN, yDim)
      self.state  = None

   def forward(self, x):
      x = torch.tensor(x).float()
      x = self.embed(x)
      if self.recur:
          x = x.view(1, 1, -1)
          x, self.state = self.hidden(x, self.state)
      else:
          x = self.hidden(x)
          x = torch.relu(x)
      x = self.action(x)
      return x

class Realm(core.Realm):
   '''Example environment overrides'''
   def step(self, decisions):
      ents = []
      stims, rewards, dones, _ = super().step(decisions)
      for idx, stim in enumerate(stims):
         env, ent = stim
         conf = self.config
         n = conf.STIM
         s = []

         for i in range(n-conf.WINDOW, n+conf.WINDOW+1):
            for j in range(n-conf.WINDOW, n+conf.WINDOW+1):
               tile = env[i, j]
               s += oneHot(tile.mat.index, 6)

         s.append(ent.resources.health.val)
         s.append(ent.resources.health.max)
         s.append(ent.resources.food.val)
         s.append(ent.resources.food.max)
         s.append(ent.resources.water.val)
         s.append(ent.resources.water.max)

         stims[idx] = s
         ents.append(ent)

      return ents, stims, rewards, dones

class Optim:
   def __init__(self, config):
      self.config  = config
      x, y         = config.INPUT_DIM, config.OUTPUT_DIM
      self.iter    = 0

      self.net     = Policy(config, x, y).eval()
      worker = ToyWorker
      if config.ENV == 'NeuralMMO-v1.3':
         worker = Worker
      self.workers = [worker.remote(config) for _ in range(config.NWORKER)]

   def run(self):
      config = self.config
      while True:
         params = param.getParameters(self.net)
         params = np.array(params)
         returns = []

         #Launch rollout workers
         t = time.time()
         for worker in self.workers:
            worker.reset.remote()
            ret = worker.run.remote(params)
            returns.append(ret)

         #Synchronize experience
         data = ray.get(returns)
         t = time.time() - t
         returns = []
         for dat in data:
            returns += dat

         #Rank transform
         entID, rewards = zip(*returns)
         n              = len(rewards)
         ranks          = np.empty(n)
         idxs           = np.argsort(rewards)
         ranks[idxs]    = np.arange(n)
         ranks          = ranks/(n-1) - 0.5
        
         #Gradient estimation
         grad = np.zeros_like(params)
         for entID, reward in zip(entID, ranks):
            np.random.seed(entID)
            noise = reward * np.random.randn(len(params))
            grad += noise

         #Log statistics
         mean = np.mean(rewards)
         std  = np.std(rewards)
         print('Iter: {}, Time: {:.2f}, Rollouts: {},  Mean: {:.2f}, Std: {:.2f}'.format(self.iter, t, n, mean, std))

         #Update parameters
         params += config.LR * config.NOISE_STD * grad
         param.setParameters(self.net, params)
         self.iter += 1

         #Rendering
         if self.iter % 1 != 0 or not config.RENDER:
            continue
         env      = gym.make(config.ENV)
         ob, done = env.reset(), False
         while not done:
            env.render()
            ob, _, _, _ = env.step(atn)
            #Obtain actions
            atn = self.net(ob)
            if config.CONTINUOUS:
               atn = torch.tanh(atn)
               atn = atn.detach().numpy().ravel()
            else:
               distribution = Categorical(logits=atn)
               atn = int(distribution.sample())

           
@ray.remote
class ToyWorker:
   def __init__(self, config):
      self.config = config

   def reset(self):
      config   = self.config
      x, y     = config.INPUT_DIM, config.OUTPUT_DIM
      self.net = Policy(config, x, y).eval()

      self.env = gym.make(config.ENV)

   def run(self, params):
      returns = []
      rewards = []

      reset = True
      done  = False

      config = self.config
      for _ in range(config.OPTIM_STEPS):
         if done:
            returns.append((seed, sum(rewards)))
            reset   = True
            rewards = []

         if reset:
            reset = False
            ob    = self.env.reset()
            seed  = np.random.randint(1, 10000000)

            np.random.seed(seed)
            noise = np.random.randn(len(params))
            param.setParameters(self.net, params + config.NOISE_STD*noise)
            self.net.state = None

         #Obtain actions
         atn = self.net(ob)
         if config.CONTINUOUS:
             atn = torch.tanh(atn)
             atn = atn.detach().numpy().ravel()
         else:
             distribution = Categorical(logits=atn)
             atn = int(distribution.sample())

         #Step environment
         ob, reward, done, _ = self.env.step(atn)
         rewards.append(reward)

      if len(returns) == 0:
         returns.append((seed, sum(rewards)))
      return returns

@ray.remote
class Worker:
   def __init__(self, config):
      self.config = config

   def reset(self):
      idx = np.random.randint(self.config.NREALM)
      self.net = Policy(self.config, 492, 4).eval()
      self.env = Realm(self.config, idx)

   def run(self, params):
      ents, obs, rewards, dones = self.env.reset()
      returns = []
      for _ in range(config.OPTIM_STEPS):
         #Collect rollouts
         for ent in dones:
            returns.append((ent.entID, ent.history.timeAlive.val-1))

         actions = {}
         for ent, ob in zip(ents, obs):
            #Perturbed rollout. Should salt the entID per realm
            np.random.seed(ent.entID)
            noise = np.random.randn(len(params))
            param.setParameters(self.net, params + config.NOISE_STD*noise)
            atn = self.net(ob)

            #Postprocess actions
            distribution = Categorical(logits=atn)
            atn = distribution.sample()
            arg = action.Direction.edges[int(atn)]
            actions[ent.entID] = {action.Move: [arg]}

         #Step environment
         ents, obs, rewards, dones = self.env.step(actions)

      return returns

if __name__ == '__main__':
   #init(None, mode='local')
   ray.init()
   config = Config()
   Optim(config).run()

