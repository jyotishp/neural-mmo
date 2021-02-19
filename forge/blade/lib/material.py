from pdb import set_trace as T

class Material:
   capacity = 0

   def __init__(self, config):
      pass

   def __eq__(self, mtl):
      return self.index == mtl.index

   def __equals__(self, mtl):
      return self == mtl

class Lava(Material):
   tex      = 'lava'
   index    = 0

class Water(Material):
   tex      = 'water'
   index    = 1

class Grass(Material):
   tex      = 'grass'
   index    = 2

class Scrub(Material):
   tex     = 'scrub'
   index   = 3

class Forest(Material):
   tex     = 'forest'
   index   = 4

   deplete = Scrub
   def __init__(self, config):
      self.respawn  = config.FOREST_RESPAWN

   def harvest(self, entity):
      pass

class Stone(Material):
   tex     = 'stone'
   index   = 5

class Slag(Material):
   tex     = 'slag'
   index   = 6

class Ore(Material):
   tex     = 'ore'
   index   = 7

   deplete = Stone
   def __init__(self, config):
      self.respawn  = config.ORE_RESPAWN

   def harvest(self, entity):
      entity.inventory.charges.scraps.amt += 1

class Stump(Material):
   tex     = 'stump'
   index   = 8

class Tree(Material):
   tex     = 'tree'
   index   = 9

   deplete = Stump
   def __init__(self, config):
      self.respawn  = config.TREE_RESPAWN

   def harvest(self, entity):
      entity.inventory.charges.shavings.amt += 1

class Fragment(Material):
   tex     = 'fragment'
   index   = 10

class Crystal(Material):
   tex     = 'crystal'
   index   = 11

   deplete = Fragment
   def __init__(self, config):
      self.respawn  = config.CRYSTAL_RESPAWN

   def harvest(self, entity):
      entity.inventory.charges.shards.amt += 1

class Meta(type):
   def __iter__(self):
      yield from self.materials

   def __contains__(self, mtl):
      if isinstance(mtl, Material):
         mtl = type(mtl)
      return mtl in self.materials

class All(metaclass=Meta):
   materials = {
      Lava, Water, Grass, Scrub, Forest,
      Stone, Slag, Ore, Stump, Tree,
      Fragment, Crystal}

class Impassible(metaclass=Meta):
   materials = {Lava, Water, Stone}

class Habitable(metaclass=Meta):
   materials = {Grass, Scrub, Forest, Ore, Tree, Crystal}

class Harvestable(metaclass=Meta):
   materials = {Forest, Ore, Tree, Crystal}
