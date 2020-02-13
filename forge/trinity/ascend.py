from pdb import set_trace as T

import ray, time
import ray.experimental.signal as signal                                      
from forge.blade.lib.utils import Queue

import os
from collections import defaultdict
                                                                              
class Packet(signal.Signal):                                                  
   def __init__(self, key, value):                                                 
      self.key   = key
      self.value = value                                                      
                                                                              
   def get_value(self):                                                       
      return self.value  

class Timed:
   '''Performance timing superclass.

   Depends on runtime and waittime decorators'''
   def __init__(self):
      self.run_time  = 0
      self.wait_time = 0

   @property
   def time(self):
      run  = self.run_time
      wait = self.wait_time
      return run, wait

   def resetLogs(self):
      self.run_time  = 0
      self.wait_time = 0

   @property
   def name(self):
      return self.__class__.__name__

   def logs(self):
      run, wait = self.time
      self.resetLogs()
      ret = {self.name: Log(run, wait)}
      return ret

class Log:
   '''Performance logging superclass

   Provides timing summaries over remote disciples'''
   def __init__(self, runTime, waitTime):
      self.run  = runTime
      self.wait = waitTime

   def merge(logs):
      run  = max([log.run for log in logs])
      wait = max([log.wait for log in logs])
      return Log(run, wait)

   def summary(logs):
      data = defaultdict(list)

      for log in logs:
         for key, val in log.items():
            data[key].append(val)         
         
      for key, logList in data.items():
         data[key] = Log.merge(logList)

      return data

   def aggregate(log):
      ret = defaultdict(dict)
      for key, val in log.items():
         ret['run'][key]  = val.run - val.wait
         ret['wait'][key] = val.wait
      return ret

def waittime(func):
   def decorated(self, *args):
      t = time.time()
      ret = func(self, *args)
      t = time.time() - t
      self.wait_time += t
      return ret

   return decorated

def runtime(func):
   def decorated(self, *args):
      t = time.time()
      ret = func(self, *args)
      t = time.time() - t
      self.run_time += t
      return ret

   return decorated

class Ascend(Timed):
   '''This module is the Ascend core and only documents the internal API.
   External documentation is available at :mod:`forge.trinity.api`'''
   def __init__(self, config, idx):
      super().__init__()
      self.inbox = defaultdict(Queue)
      self.idx   = idx

   def put(self, packet, key):
      self.inbox[key].put(packet)

   def recv(self, key):
      return self.inbox[key]

   @staticmethod
   def send(dests, packet, key):
      if type(dests) != list:
         dests = [dests]

      for dst in dests:
         try:
            dst.put.remote(packet, key)
         except:
            print('Error at {}'.format(dst))

     
   #@staticmethod
   #def clear():
   #   os.system('clear')

   '''
   def send(key, data):
      packet = Packet(key, data)
      signal.send(packet)

   def recv(source, key=None, timeout=0.01):
      packets = signal.receive(source, timeout)
      ret = defaultdict(list) 
      for p in packets:
         p = p[1]
         assert type(p) != signal.ErrorSignal, p.error
         ret[p.key].append(p.value)

      if key is None:
         return ret
      return ret[key]
   '''

   def init(disciple, config, n, *args):
      remote   = Ascend.isRemote(disciple)
      disciple = Ascend.localize(disciple, remote)
      return [disciple(config, idx, *args) for idx in range(n)]

   def distribute(disciples, *args, shard=None):
      arg, rets = args, []
      for discIdx, disciple in enumerate(disciples):
         remote = Ascend.isRemote(disciple)
         step   = Ascend.localize(disciple.step, remote)

         arg = []
         for shardIdx, e in enumerate(args):
            if shard is None:
               arg = args
            elif shard[shardIdx]:
               arg.append(e[discIdx])
            else:
               arg.append(e)

         arg = tuple(arg)
         rets.append(step(*arg))

      return rets

   @waittime
   def synchronize(self, rets):
      try:
         return ray.get(rets)
      except:
         return rets

   def step(disciples, *args, shard=False):
      rets = Ascend.distribute(disciples, *args)
      return Ascend.synchronize(rets)

   def discipleLogs(self):
      logs = []
      for e in self.disciples:
         log = e.logs
         try:
            log = ray.get(log.remote())
         except:
            log = log()
         logs.append(log)

      logs = Log.summary(logs)
      return logs

 
   def localize(func, remote):
      return func if not remote else func.remote

   def isRemote(obj):
      return hasattr(obj, 'remote') or hasattr(obj, '__ray_checkpoint__')
