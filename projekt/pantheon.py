from pdb import set_trace as T

import ray
import ray.experimental.signal as signal
import time

from collections import defaultdict

from forge.blade.lib.log import BlobSummary

from forge.ethyr.torch import Model
from forge.trinity.ascend import Ascend, Packet, runtime, waittime

from forge.ethyr.experience import Rollout, RolloutManager

from forge.ethyr.torch import optim
from forge.ethyr.torch.param import getParameters, setParameters

import projekt

@ray.remote
class Pantheon(Ascend):
   '''Cluster level infrastructure layer

   This module aggregates gradients across all server level 
   environments and updates model weights using Adam.

   It also demonstrates logging and snapshotting functionality 
   through the Quill and Model libraries, respectively.'''

   def __init__(self, config, idx):
      '''Initializes a copy of the model, which keeps
      track of the weights for the optimizer.

      Args:
         trinity : A Trinity object as shown in __main__
         config  : A Config object as shown in __main__
         idx     : Unused hardware index
      '''
      super().__init__(config, idx)
      self.config   = config
      self.rollouts = {}                                                      
      self.n        = 0

      device       = config.DEVICE
      self.net     = projekt.Policy(config).to(device)
      self.manager = RolloutManager(config)

   def recvModel(self):
      packets = Ascend.recv([self.trinity.cluster], 'Model')
      if len(packets) > 0:
         weights = packets[-1]
         setParameters(self.net, weights)

   @waittime
   def recvExperience(self):
      return Ascend.recv(self.trinity.sword, 'Experience', timeout=None)

   def run(self, trinity):
      self.trinity = trinity
      while True:
         self.step()
         Ascend.send('Utilization', self.logs())

   @runtime
   def step(self):
      '''Broadcasts updated weights to server level God optimizer nodes.
      Performs an Adam step once optimizers return a batch of gradients.

      Returns:
         perf  : Log message describing agent performance
         stats : Log message describing data collected
         log   : Dictionary of logs containing infrastructure usage data
      ''' 
      self.recvModel()
      for packet in self.recvExperience():
         self.manager.collectInputs(packet)
         self.net(packet, self.manager)
         rollouts, _ = self.manager.step()

         for k, rollout in rollouts.items():
            assert k not in self.rollouts
            self.rollouts[k] = rollout
            self.n += rollout.time

      if self.n > self.config.SERVER_UPDATES:
         rollouts      = self.rollouts
         self.rollouts = {}

         optim.backward(rollouts, self.config)                                
         grads = self.net.grads() 
         Ascend.send('Gradients', grads)
         Ascend.send('Updates', (len(rollouts), self.n))
         self.n = 0


