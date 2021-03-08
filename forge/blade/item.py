from pdb import set_trace as T
import random

from forge.blade.lib.enums import Tier

class Item:
   def __init__(self, config, level):
      self.config = config
      self.level  = level

   @property
   def packet(self):
      return {'item':  self.__class__.__name__,
              'level': self.level}

class Stack(Item):
   def __init__(self, config, level):
      super().__init__(config, level)
      capacity      = level
      self.capacity = capacity
      self.quantity = capacity

   @property
   def packet(self):
      packet = {'capacity': self.capacity,
                'quantity': self.quantity}
      return {**packet, **super().packet}

   def use(self):
      assert self.quantity > 0
      self.quantity -= 1

      if self.quantity > 0:
         return True

      return False

class Gold(Item):
   def __init__(self, config):
      super().__init__(config, level=0)
      self.quantity = 0

   @property
   def packet(self):
      packet = {'quantity': self.quantity}
      return {**packet, **super().packet}

class Equipment(Item):
   @property
   def packet(self):
     packet = {'color': self.color.packet()}
     return {**packet, **super().packet}

   @property
   def color(self):
     if self.level == 0:
        return Tier.BLACK
     if self.level < 10:
        return Tier.WOOD
     elif self.level < 20:
        return Tier.BRONZE
     elif self.level < 40:
        return Tier.SILVER
     elif self.level < 60:
        return Tier.GOLD
     elif self.level < 80:
        return Tier.PLATINUM
     else:
        return Tier.DIAMOND

class Hat(Equipment):
   def __init__(self, config, level):
      super().__init__(config, level)
      self.defense = config.EQUIPMENT_DEFENSE(level)

class Top(Equipment):
   def __init__(self, config, level):
      super().__init__(config, level)
      self.defense = config.EQUIPMENT_DEFENSE(level)

class Bottom(Equipment):
   def __init__(self, config, level):
      super().__init__(config, level)
      self.defense = config.EQUIPMENT_DEFENSE(level)

class Weapon(Equipment):
   def __init__(self, config, level):
      super().__init__(config, level)
      self.offense = config.EQUIPMENT_OFFENSE(level)

class Ammunition(Stack):
   def __init__(self, config, level):
      super().__init__(config, level)
      self.minDmg, self.maxDmg = config.DAMAGE_AMMUNITION(level)

   @property
   def packet(self):
      packet = {'minDmg': self.minDmg,
                'maxDmg': self.maxDmg}
      return {**packet, **super().packet}

   def use(self, skill):
      if skill.__name__ == 'Melee':
         return super().use(Item.Scrap)
      if skill.__name__ == 'Range':
         return super().use(Item.Shaving)
      if skill.__name__ == 'Mage':
         return super().use(Item.Shard)

      system.exit(0, 'Ammunition.Use: invalid skill {}'.format(skill))      

   def damage(self):
      return random.randint(self.minDmg, self.maxDmg)
  
class Scrap(Ammunition): pass
class Shaving(Ammunition): pass
class Shard(Ammunition): pass

class Consumable(Item):
   def __init__(self, config, level):
      super().__init__(config, level)
      self.restore = level

class Food(Consumable):
   def use(self, entity):
      entity.resources.food.increment(self.restore)
      entity.resources.water.increment(self.restore)

class Potion(Consumable):
   def use(self, entity):
      entity.resources.health.increment(self.restore)
 
