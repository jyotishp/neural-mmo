from pdb import set_trace as T                                                
import numpy as np
                                                                              
import ray                                                                    
from forge.blade.lib.log import BlobSummary

from forge.ethyr.torch import Model                                           
from forge.ethyr.torch.param import getParameters                             

from forge.trinity import Ascend
                                                                              
@ray.remote                                                                   
class Cluster:                                                                
   def __init__(self, config, policy):
      #Train until AGI emerges
      self.model = Model(policy, config)
      self.model.printParams()

   def sendModel(self):                                                       
      weights = getParameters(self.model.net)
      Ascend.send('Model', weights)

   def log(self, logs):
      if len(logs) > 0:
         runs, waits = [], []
         for log in logs:
            for k, v in log.items():
               runs.append(v.run)
               waits.append(v.wait)

         run  = np.mean(runs)
         wait = np.mean(waits)
      else:
         run = wait = 0

      return run, wait
 
   def logs(self):
      pantheonLogs  = Ascend.recv('PantheonLogs', self.trinity.pantheon)
      godLogs       = Ascend.recv('GodLogs', self.trinity.god)
      #swordLogs     = Ascend.recv('SwordLogs', self.trinity.sword)

      run, wait = self.log(pantheonLogs)
      print('Pantheon - Run: ', run, ', Wait: ', wait)

      run, wait = self.log(godLogs)
      print('God - Run: ', run, ', Wait: ', wait)

   def run(self, trinity):
      self.trinity = trinity
      self.sendModel()
      while True:
         grads = Ascend.recv('Gradients', self.trinity.pantheon)

         if len(grads) > 0:                                                   
            perf = self.model.step(grads, [], [], 0.0)
            self.sendModel()

         #self.logs()
