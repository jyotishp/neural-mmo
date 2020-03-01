from pdb import set_trace as T
from collections import defaultdict
from forge.blade.lib.enums import Material
from forge.blade.lib import enums
from copy import deepcopy
import os

import numpy as np
import json, pickle
import time
import ray

from tqdm import tqdm

from forge.trinity.ascend import Ascend
from forge.blade.systems import visualizer

class Stat:
   def __init__(self):
      self.val = 0
      self.max = 0

class Bar(tqdm):
   def __init__(self, position=0, title='title', form=None):
      lbar = '{desc}: {percentage:3.0f}%|'
      bar = '{bar}'
      rbar  = '| [' '{elapsed}{postfix}]'
      fmt = ''.join([lbar, bar, rbar])

      if form is not None:
         fmt = form

      super().__init__(
            total=100,
            position=position,
            bar_format=fmt)

      self.title(title)

   def percent(self, val):
      self.update(100*val - self.n)

   def title(self, txt):
      self.desc = txt
      self.refresh()

class Logger:                                                                 
   def __init__(self, middleman):                                             
      self.items     = 'reward lifetime value'.split()                              
      self.middleman = middleman                                              
      self.tick      = 0                                                      
                                                                              
   def update(self, lifetime_mean, reward_mean, value_mean,
              lifetime_std, reward_std, value_std):
      data = {}                                                               
      data['lifetime'] = lifetime_mean
      data['reward']   = reward_mean
      data['value']    = value_mean
      data['lifetime_std']  = lifetime_std
      data['reward_std']    = reward_std
      data['value_std']     = value_std
      data['tick']     = self.tick                                            
                                                                              
      self.tick += 1                                                          
      self.middleman.setData.remote(data)

class BlobSummary:
   def __init__(self):
      self.nRollouts = 0
      self.nUpdates  = 0

      self.lifetime = []
      self.reward   = [] 
      self.value    = []

   def add(self, blobs):
      for blob in blobs:
         self.nRollouts += blob.nRollouts
         self.nUpdates  += blob.nUpdates

         self.lifetime += blob.lifetime
         self.reward   += blob.reward
         self.value    += blob.value

      return self

#Agent logger
class Blob:
   def __init__(self, entID, annID, lifetime, exploration): 
      self.exploration = exploration
      self.lifetime    = lifetime

      self.entID = entID 
      self.annID = annID

#Static blob analytics
class InkWell:
   def __init__(self):
      self.util = defaultdict(lambda: defaultdict(list))
      self.stat = defaultdict(lambda: defaultdict(list))

   def summary(self):
      return

   def step(self, utilization, statistics):
      self.utilization(utilization)
      self.statistics(statistics)

   def statistics(self, logs):
      for rollouts, updates in logs['Pantheon_Updates']:
         self.stat['Performance']['Epochs'].append(1)
         self.stat['Performance']['Rollouts'].append(rollouts)
         self.stat['Performance']['Updates'].append(updates)

      for blobs in logs['Realm_Logs']:
         for blob in blobs:
            #self.stat['Blobs'].append(blob)
            self.stat['Agent']['Population'].append(len(blobs))
            self.stat['Agent']['Lifetime'].append(blob.lifetime)
            for tile, count in blob.exploration.items():
               self.stat['Agent'][tile].append(count)

   def utilization(self, logs):
      for k, vList in logs.items():
         for v in vList:
            self.util[k]['run'].append(v.run)
            self.util[k]['wait'].append(v.wait)
            #self.util[k]['percent'].append(v.run / (v.run + v.wait))

   def summary(self):
      summary = defaultdict(dict)
      for log, vDict in self.stat.items():
         for k, v in vDict.items():
            if log not in self.stat:
               continue
            stat = Stat()
            val, mmax = v[-1], max(v)
            stat.val = val
            stat.max = mmax
            if 0==val==mmax:
               stat.percentage = 0
            else:
               stat.percentage = val / (val + mmax)
            summary[log][k] = stat
      
      for log, vDict in self.util.items():
         for k, v in vDict.items():
            if log not in self.util:
               continue
            stat = Stat()
            stat.val = v[-1]
            stat.max = max(v)
            summary[log][k] = stat
      return summary
            
   def unique(blobs):
      tiles = defaultdict(list)
      for blob in blobs:
          for t, v in blob.unique.items():
             tiles['unique_'+t.tex].append(v)
      return tiles

   def counts(blobs):
      tiles = defaultdict(list)
      for blob in blobs:
          for t, v in blob.counts.items():
             tiles['counts_'+t.tex].append(v)
      return tiles

   def explore(blobs):
      tiles = defaultdict(list)
      for blob in blobs:
          for t in blob.counts.keys():
             counts = blob.counts[t]
             unique = blob.unique[t]
             if counts != 0:
                tiles['explore_'+t.tex].append(unique / counts)
      return tiles

   def lifetime(blobs):
      return {'lifetime':[blob.lifetime for blob in blobs]}
 
   def reward(blobs):
      return {'reward':[blob.reward for blob in blobs]}
  
   def value(blobs):
      return {'value': [blob.value for blob in blobs]}

@ray.remote
class Quill(Ascend):
   def __init__(self, config, idx):
      super().__init__(config, 0)
      self.inkwell = InkWell()
      self.config     = config
      self.stats      = defaultdict(Stat)
      self.epochs     = 0
      self.rollouts   = 0
      self.updates    = 0

   def init(self, trinity):
      self.trinity = trinity
      return 'Quill', 'Initialized'

   def step(self):
      utilization, statistics = {}, {}

      #Utilization
      for key in 'Pantheon God Sword'.split():
         utilization[key] = self.recv(key + '_Utilization')

      #Statistics
      for key in 'Pantheon_Updates God_Logs Realm_Logs'.split():
         statistics[key] = self.recv(key)
 
      self.inkwell.step(utilization, statistics)
      return self.inkwell.summary()

#Log wrapper and benchmarker
class Benchmarker:
   def __init__(self, logdir):
      self.benchmarks = {}

   def wrap(self, func):
      self.benchmarks[func] = Utils.BenchmarkTimer()
      def wrapped(*args):
         self.benchmarks[func].startRecord()
         ret = func(*args)
         self.benchmarks[func].stopRecord()
         return ret
      return wrapped

   def bench(self, tick):
      if tick % 100 == 0:
         for k, benchmark in self.benchmarks.items():
            bench = benchmark.benchmark()
            print(k.__func__.__name__, 'Tick: ', tick,
                  ', Benchmark: ', bench, ', FPS: ', 1/bench)
 

