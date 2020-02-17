from pdb import set_trace as T

import ray, time
import asyncio

import os
from collections import defaultdict
                                                                              
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

@ray.remote
class AsyncQueue:
   def __init__(self):
      self.inbox = defaultdict(asyncio.Queue)

   async def put(self, packet, key):
      print('Put data')
      await self.inbox[key].put(packet)

   async def get(self, key):
      data = []
      while True:
         try:
            pkt = self.inbox[key].get_nowait()
            data.append(pkt)
         except asyncio.QueueEmpty:
            break
      return data


class AscendWrapper:
   def __init__(self, disciple, queue):
      self.disciple = disciple
      self.queue    = queue

class Ascend(Timed):
   '''This module is the Ascend core and only documents the internal API.
   External documentation is available at :mod:`forge.trinity.api`'''
   def __init__(self, config, idx):
      super().__init__()
      self.config = config
      self.idx    = idx

   def setQueue(self, queue):
      self.queue = queue

   def init(disciple, config, n, *args):
      disciple = Ascend.localize(disciple)
      actors = []
      for idx in range(n):
         actor = disciple(config, idx, *args)
         queue = AsyncQueue.remote()

         setQueue = Ascend.localize(actor.setQueue)
         setQueue(queue)

         actor = AscendWrapper(actor, queue)
         actors.append(actor)

      return actors
         
   @staticmethod
   def send(dests, packet, key):
      if type(dests) != list:
         dests = [dests]

      for dst in dests:
         try:
            dst.queue.put.remote(packet, key)
         except Exception as e:
            print('Error at {}: {}'.format(dst, e))

   def recv(self, key):
      func = Ascend.localize(self.queue.get)
      return Ascend.get(func(key))

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
      return Ascend.get(rets)

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

   def get(rets):
      try:
         return ray.get(rets)
      except:
         return rets

   def localize(obj):
      remote = Ascend.isRemote(obj) 
      return Ascend.setRemote(obj, remote)
      
   def setRemote(func, remote):
      return func if not remote else func.remote

   def isRemote(obj):
      #Remote function
      if hasattr(obj, 'remote'):
         return True
      #Remote actor
      if hasattr(obj, '__ray_checkpoint__'):
         return True

      #Local function or actor
      return False


