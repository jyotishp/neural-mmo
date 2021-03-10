from pdb import set_trace as T
from forge.blade import core
import os

from forge.blade.systems.ai import behavior

class Base(core.Config):
   '''Base config for RLlib Models

   Extends core Config, which contains environment, evaluation,
   and non-RLlib-specific learning parameters'''
   
   #Hardware Scale
   NUM_WORKERS             = 4
   NUM_GPUS_PER_WORKER     = 0
   NUM_GPUS                = 1
   LOCAL_MODE              = False

   #Memory/Batch Scale
   TRAIN_BATCH_SIZE        = 400000
   ROLLOUT_FRAGMENT_LENGTH = 100

   #Optimization Scale
   SGD_MINIBATCH_SIZE      = 128
   NUM_SGD_ITER            = 1

   #Model Parameters 
   #large-map:        Large maps baseline
   #small-map:        Small maps baseline
   #scripted-combat:  Scripted with combat
   #scripted-forage:  Scripted without combat
   #current:          Resume latest checkpoint
   #None:             Train from scratch
   MODEL                   = 'current'
   N_AGENT_OBS             = 100
   NPOLICIES               = 1
   HIDDEN                  = 64
   EMBED                   = 64

   #Scripted model parameters
   SCRIPTED_BACKEND        = 'dijkstra' #Or 'dynamic_programming'
   SCRIPTED_EXPLORE        = True       #Intentional exploration

   DEV_COMBAT = False


class LargeMaps(Base):
   '''Large scale Neural MMO training setting

   Features up to 1000 concurrent agents and 1000 concurrent NPCs,
   1km x 1km maps, and 5/10k timestep train/eval horizons

   This is the default setting as of v1.5 and allows for large
   scale multiagent research even on relatively modest hardware'''

   NAME                    = __qualname__
   MODEL                   = 'large-map'

   PATH_MAPS               = core.Config.PATH_MAPS_LARGE

   TRAIN_HORIZON           = 5000
   EVALUATION_HORIZON      = 10000

   NENT                    = 1024
   NMOB                    = 1024


class SmallMaps(Base):
   '''Small scale Neural MMO training setting

   Features up to 128 concurrent agents and 32 concurrent NPCs,
   60x60 maps (excluding the border), and 1000 timestep train/eval horizons.
   
   This setting is modeled off of v1.1-v1.4 It is appropriate as a quick train
   task for new ideas, a transfer target for agents trained on large maps,
   or as a primary research target for PCG methods.'''

   NAME                    = __qualname__
   MODEL                   = 'small-map'
   SCRIPTED_EXPLORE        = False

   TRAIN_HORIZON           = 1000
   EVALUATION_HORIZON      = 1000

   NENT                    = 128
   NMOB                    = 32

   #Path settings
   PATH_MAPS               = core.Config.PATH_MAPS_SMALL
   PATH_ROOT               = os.path.join(os.getcwd(), PATH_MAPS, 'map')

   #Outside-in map design
   SPAWN_CENTER            = False
   INVERT_WILDERNESS       = True
   WILDERNESS              = False

   #Terrain generation parameters
   TERRAIN_MODE            = 'contract'
   TERRAIN_LERP            = False
   TERRAIN_SIZE            = 80 
   TERRAIN_OCTAVES         = 1
   TERRAIN_FOREST_LOW      = 0.30
   TERRAIN_FOREST_HIGH     = 0.75
   TERRAIN_GRASS           = 0.715
   TERRAIN_ALPHA           = -0.025
   TERRAIN_BETA            = 0.035

   #Entity spawning parameters
   PLAYER_SPAWN_ATTEMPTS   = 1
   NPC_LEVEL_MAX           = 35
   NPC_LEVEL_SPREAD        = 5
   NPC_SPAWN_PASSIVE       = 0.00
   NPC_SPAWN_NEUTRAL       = 0.60
   NPC_SPAWN_AGGRESSIVE    = 0.80

class Dev(SmallMaps):
   MODEL                   = 'scripted-combat' 

   NTILE                   = 16

   PATH_MAPS_DEV           = os.path.join(core.Config.PATH_MAPS, 'dev')
   PATH_MAPS               = PATH_MAPS_DEV

   ORE_RESPAWN       = 0.01
   '''Probability that a harvested ore tile will regenerate each tick'''

   TREE_RESPAWN      = 0.01
   '''Probability that a harvested tree tile will regenerate each tick'''

   CRYSTAL_RESPAWN   = 0.01
   '''Probability that a harvested crystal tile will regenerate each tick'''

   HERB_RESPAWN      = 0.01
   '''Probability that a harvested herb tile will regenerate each tick'''

   FISH_RESPAWN      = 0.01
   '''Probability that a harvested fish tile will regenerate each tick'''


   N_AMMUNITION      = 3
   '''Number of inventory spaces for ammunition'''

   N_CONSUMABLES     = 6
   '''Number of inventory spaces for ammunition'''

   N_LOOT            = 8
   '''Number of inventory spaces for ammunition'''

   N_ITEM            = 10


   SPAWN_CLUSTERS          = 15
   SPAWN_UNIFORMS          = 50

   DEV_COMBAT = True

   def EQUIPMENT_DEFENSE(level):
      return level / 4

   def EQUIPMENT_OFFENSE(level):
      return level / 4

   def DAMAGE_AMMUNITION(level):
      return level // 5 + 1, level // 3 + 1

   def DAMAGE_MELEE(level):
      return round(10 + level*70/99)

   def DAMAGE_RANGE(level):
      return round(3 + level*32/99)

   def DAMAGE_MAGE(level):
      return round(1 + level*24/99)

   def RESTORE(level):
      return level

class Debug(SmallMaps):
   '''Debug Neural MMO training setting

   A version of the SmallMap setting with greatly reduced batch parameters.
   Only intended as a tool for identifying bugs in the model or environment'''
   MODEL                   = None
   LOCAL_MODE              = True
   NUM_WORKERS             = 1

   TRAIN_BATCH_SIZE        = 400
   TRAIN_HORIZON           = 200
   EVALUATION_HORIZON      = 50

   HIDDEN                  = 2
   EMBED                   = 2
