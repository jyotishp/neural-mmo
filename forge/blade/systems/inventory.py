from forge.blade.item import item, armor
from forge.blade.systems import skill as Skill

class Charge:
   def __init__(self):
      self.amt  = 0
      self.used = 0

   def use(self):
      if self.amt > 0:
         self.amt  -= 1
         self.used += 1
         return True
      return False

   @property
   def heldOrUsed(self):
      return self.amt + self.used

class Charges:
   def __init__(self, config):
      self.scraps   = Charge()
      self.shavings = Charge()
      self.shards   = Charge()

   def use(self, skill):
      if skill == Skill.Melee:
         return self.scraps.use()
      if skill == Skill.Range:
         return self.shavings.use()
      if skill == Skill.Mage:
         return self.shards.use()

class Food:
   def __init__(self, config):
      self.N    = config.MAX_FOOD
      self.food = 0

   def __len__(self):
      return len(self.data)

   def add(self):
      if len(self) == self.N:
         return
      self.food += 1

   def remove(self, food):
      if self.food == 0:
         return False

      self.food -= 1
      return True 
      
class Inventory:
   def __init__(self, realm):
      config       = realm.config
      self.charges = Charges(config)
      self.food    = Food(config)
