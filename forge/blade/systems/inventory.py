from pdb import set_trace as T

import inspect

from forge.blade import Item
from forge.blade.systems import skill as Skill

class Pouch:
   def __init__(self, capacity):
      self.capacity = capacity
      self.items    = []

   @property
   def space(self):
      return self.capacity - len(self.items)

   def packet(self):
      return [item.packet for item in self.items]

   def add(self, item):
      space = self.space
      err = '{} out of space for {}'
      assert space, err.format(self, item) 
      self.items.append(item)

   def remove(self, item):
      items = self.__contains__(item)
      err = '{} does not contain {}'
      assert items, err.format(self, item) 
      self.items.remove(items[0])

   def use(self, item):
      items = self.__contains__(item)

      if not items:
         return False

      item = items[0]
      if not item.use():
         return False

      return item

   def __contains__(self, item):
      items = []
      for itm in self.items:
         if inspect.isclass(item) and type(itm) == item:
            items.append(itm)
         elif not inspect.isclass(item) and isinstance(item, type(itm)):
            items.append(itm)
      return items

class Loadout:
   def __init__(self, realm, hat=0, top=0, bottom=0, weapon=0):
      self.hat    = Item.Hat(realm, hat)
      self.top    = Item.Top(realm, top)
      self.bottom = Item.Bottom(realm, bottom)
      self.weapon = Item.Weapon(realm, weapon)

   @property
   def items(self):
      return [self.hat, self.top, self.bottom, self.weapon]

   @property
   def defense(self):
      return round(self.hat.defense
                      + self.top.defense
                      + self.bottom.defense)

   @property
   def level(self):
      return 0.25 * (self.hat.level.val
                   + self.top.level.val
                   + self.bottom.level.val
                   + self.weapon.level.val)

   @property
   def offense(self):
      return round(self.weapon.offense)

   def packet(self):
      packet = {}

      packet['hat']    = self.hat.packet
      packet['top']    = self.top.packet
      packet['bottom'] = self.bottom.packet
      packet['weapon'] = self.weapon.packet

      return packet

class Inventory:
   def __init__(self, realm):
      config           = realm.config
      self.config      = config

      self.gold        = Item.Gold(realm)
      self.equipment   = Loadout(realm)
      self.ammunition  = Pouch(config.N_AMMUNITION)
      self.consumables = Pouch(config.N_CONSUMABLES)
      self.loot        = Pouch(config.N_LOOT)

   def packet(self):
      data                = {}

      data['gold']        = self.gold.packet
      data['ammunition']  = self.ammunition.packet()
      data['consumables'] = self.consumables.packet()
      data['loot']        = self.loot.packet()
      #print(self.loot.packet())

      return data

   @property
   def items(self):
      return (self.equipment.items + [self.gold] + self.ammunition.items
            + self.consumables.items + self.loot.items)

   @property
   def dataframeKeys(self):
      return [e.instanceID for e in self.items[5:]]

   def remove(self, item):
      if self.loot.__contains__(item):
         self.loot.remove(item)
      elif self.consumables.__contains__(item):
         self.consumables.remove(item)
      elif self.ammunition.__contains__(item):
         self.ammunition.remove(item)
      #elif self.equipment.__contains__(item):
      #   self.equipment.remove(item)
      else:
         T()
         system.exit(0, "{} not in inv".format(item))

   def receiveItems(self, items):
      if type(items) != list:
         items = [items]
      for item in items:
         #msg = 'Received Drop: Level {} {}'
         #print(msg.format(item.level, item.__class__.__name__))

         if isinstance(item, Item.Gold):
            self.gold.quantity += item.quantity.val
         elif isinstance(item, Item.Hat) and item.level > self.equipment.hat.level:
            self.equipment.hat = item
         elif isinstance(item, Item.Top) and item.level > self.equipment.top.level:
            self.equipment.top = item
         elif isinstance(item, Item.Bottom) and item.level > self.equipment.bottom.level:
            self.equipment.bottom = item
         elif isinstance(item, Item.Weapon) and item.level > self.equipment.weapon.level:
            self.equipment.weapon = item
         elif isinstance(item, Item.Ammunition) and self.ammunition.space:
            self.ammunition.add(item)
         elif isinstance(item, Item.Consumable) and self.consumables.space:
            self.consumables.add(item)
         elif self.loot.space:
            self.loot.add(item)

