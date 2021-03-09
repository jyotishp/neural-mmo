from pdb import set_trace as T
import random

from forge.blade.io.stimulus import Static
from forge.blade.lib.enums import Tier

class Item:
   INSTANCE_ID = 1
   def __init__(self, realm, level=0, capacity=0, quantity=0):
      self.instanceID   = self.INSTANCE_ID
      Item.INSTANCE_ID += 1

      self.config   = realm.config
      self.realm    = realm  

      self.index    = Static.Item.Index(realm.dataframe, self.instanceID, self.ITEM_ID)
      self.level    = Static.Item.Level(realm.dataframe, self.instanceID, level)
      self.capacity = Static.Item.Capacity(realm.dataframe, self.instanceID, capacity)
      self.quantity = Static.Item.Quantity(realm.dataframe, self.instanceID, quantity)

      realm.dataframe.init(Static.Item, self.instanceID, None)

   @property
   def packet(self):
      return {'item':  self.__class__.__name__,
              'level': self.level}

class Stack(Item):
   def __init__(self, realm, level):
      super().__init__(realm, level)
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
   ITEM_ID = 1

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
   ITEM_ID = 2
   def __init__(self, realm, level):
      super().__init__(realm, level)
      self.defense = realm.config.EQUIPMENT_DEFENSE(level)

class Top(Equipment):
   ITEM_ID = 3
   def __init__(self, realm, level):
      super().__init__(realm, level)
      self.defense = realm.config.EQUIPMENT_DEFENSE(level)

class Bottom(Equipment):
   ITEM_ID = 4
   def __init__(self, realm, level):
      super().__init__(realm, level)
      self.defense = realm.config.EQUIPMENT_DEFENSE(level)

class Weapon(Equipment):
   ITEM_ID = 5
   def __init__(self, realm, level):
      super().__init__(realm, level)
      self.offense = realm.config.EQUIPMENT_OFFENSE(level)

class Ammunition(Stack):
   def __init__(self, realm, level):
      super().__init__(realm, level)
      self.minDmg, self.maxDmg = realm.config.DAMAGE_AMMUNITION(level)

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
  
class Scrap(Ammunition):
   ITEM_ID = 6

class Shaving(Ammunition):
   ITEM_ID = 7

class Shard(Ammunition):
   ITEM_ID = 8

class Consumable(Item):
   def __init__(self, realm, level):
      super().__init__(realm, level)
      self.restore = level

class Food(Consumable):
   ITEM_ID = 9
   def use(self, entity):
      entity.resources.food.increment(self.restore)
      entity.resources.water.increment(self.restore)

class Potion(Consumable):
   ITEM_ID = 10
   def use(self, entity):
      entity.resources.health.increment(self.restore)
 
