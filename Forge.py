'''Main file for neural-mmo/projekt demo

In lieu of a simplest possible working example, I
have chosen to provide a fully featured copy of my
own research code. Neural MMO is persistent with 
large and variably sized agent populations -- 
features not present in smaller scale environments.
This causes differences in the training loop setup
that are fundamentally necessary in order to maintain
computational efficiency. As such, it is most useful
to begin by considering this full example.

I have done my best to structure the demo code
heirarchically. Reading only pantheon, god, and sword 
in /projeckt will give you a basic sense of the training
loop, infrastructure, and IO modules for handling input 
and output spaces. From there, you can either use the 
prebuilt IO networks in PyTorch to start training your 
own models immediately or dive deeper into the 
infrastructure and IO code.'''

#My favorite debugging macro
from pdb import set_trace as T 
import argparse
import numpy as np
import time

import ray
import ray.experimental.signal as signal

from forge.blade import lib
from forge.blade.core import Realm
from forge.blade.lib.log import TestQuill, Bar

from forge.trinity import Trinity
from forge.ethyr.torch import Model
from forge.ethyr.torch.param import getParameters

from experiments import Experiment, Config
from projekt import Cluster, Pantheon, God, Sword, Policy

def parseArgs(config):
   '''Processes command line arguments'''
   parser = argparse.ArgumentParser('Projekt Godsword')
   parser.add_argument('--ray', type=str, default='default', 
         help='Ray mode (local/default/remote)')
   parser.add_argument('--render', action='store_true', default=False, 
         help='Render env')
   parser.add_argument('--log', action="store_true",
         help='Log data on visualizer exit. Default file is timestamp, filename overwrite with --name')
   parser.add_argument('--name', default='log',
         help='Name of file to save json data to')
   parser.add_argument('--load-exp', action="store_true",
         help='Loads saved json into visualizer with name specified by --name')

   return parser.parse_args()

def render(trinity, config, args):
   """Runs the environment with rendering enabled. To pull
   up the Unity client, run ./client.sh in another shell.

   Args:
      trinity : A Trinity object as shown in __main__
      config  : A Config object as shown in __main__
      args    : Command line arguments from argparse

   Notes:
      Rendering launches a WebSocket server with a fixed tick
      rate. This is a blocking call; the server will handle 
      environment execution using the provided tick function.
   """

   #Prevent accidentally overwriting the trained model
   config.LOAD = True
   config.TEST = True
   config.BEST = True

   #Init infra in local mode
   lib.ray.init(config, 'local')

   #Instantiate environment and load the model,
   #Pass the tick thunk to a twisted WebSocket server
   god   = trinity.god.remote(trinity, config, idx=0)
   model = Model(Policy, config).load(None, config.BEST).weights
   env   = god.getEnv.remote()
   god.tick.remote(model)

   #Start a websocket server for rendering. This requires
   #forge/embyr, which is automatically downloaded from
   #jsuarez5341/neural-mmo-client in scripts/setup.sh
   from forge.embyr.twistedserver import Application
   Application(env, god.tick.remote)

class LogBars:
   def __init__(self):
      self.perf     = Bar(title='', position=0,
            form='[Elapsed: {elapsed}] {desc}')
      self.pantheon = Bar(title='Pantheon', position=1)
      self.god      = Bar(title='God     ', position=2)
      self.sword    = Bar(title='Sword   ', position=3)

      self.len      = 0
      self.pos      = 4
      self.stats    = {}

   def log(self, percent, bar):
      bar.refresh()
      if percent != 0:
         bar.percent(percent)

   def step(self, packet):
      self.log(packet['Pantheon'], self.pantheon)
      self.log(packet['God'], self.god)
      self.log(packet['Sword'], self.sword)

      if 'Performance' in packet:
         data                      = packet['Performance']
         epochs, rollouts, updates = packet['Updates']

         self.perf.title('Epochs: {}, Rollouts: {}, Updates: {}'.format(
               epochs, rollouts, updates))

         for k, v in data.items():
            self.len = max(self.len, len(k))
            if k not in self.stats:
               self.stats[k] = Bar(title='', position=self.pos, form='{desc}')
               self.pos += 1

            bar = self.stats[k]
            l = str(self.len)
            bar.title(
                  ('   {: <'+l+'}: {:.2f}<{:.2f}'
                  ).format(k.capitalize(), v.val, v.max))


if __name__ == '__main__':
   #Experiment + command line args specify configuration
   #Trinity specifies Cluster-Server-Core infra modules
   config  = Experiment('pop', Config).init()
   trinity = Trinity(Cluster, Pantheon, God, Sword, TestQuill)
   args    = parseArgs(config)

   bars = LogBars()


   #Blocking call: switches execution to a
   #Web Socket Server module
   if args.render:
      render(trinity, config, args)

   #Train until AGI emerges
   trinity.init(config, args, Policy)
   while True:
      packet = trinity.quill.step.remote()
      packet = ray.get(packet)
      bars.step(packet)


