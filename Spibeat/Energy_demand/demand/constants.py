"""
Global Physical & Simulation Constants
"""

# ============================================================
# WATER / DHW CONSTANTS
# ============================================================

CP_WATER = 4180.0                 # J/kgK
T_SOIL = 12.0                     # °C
HOT_WATER_TEMP = 45.0             # °C
COP_DHW = 3.5                     # Heat pump COP

# ============================================================
# PIPE SYSTEM
# ============================================================

PIPE_LENGTH_M = 50.0              # meters
PIPE_U_VALUE = 0.7                # W/m2K
RECOVERABLE_FRACTION = 0.3        # fraction
SAFETY_FACTOR = 1.2               # oversizing

# ============================================================
# SIMULATION SETTINGS
# ============================================================

SIMULATION_YEAR = 2023
HOURS_PER_YEAR = 8760

# ============================================================
# UNIT CONVERSIONS
# ============================================================

J_TO_KWH = 1 / 3_600_000
W_TO_KW = 1 / 1000


"""
Global Simulation Constants
"""

# ------------------------------------------------
RHO = 1000.0
G = 9.81
ETA = 0.6
FLOOR_HEIGHT_M = 3.0
RHO_AIR = 1.2
C_A = 1005.0
H_WE = 2_430_000.0
P_ATM = 97500.0
DEFAULT_QCSMAX = 120.0
# Tank surface area approximation
TANK_SURFACE_COEFF = 0.5   # coefficient for tank surface area calculation
TANK_SURFACE_EXP = 0.66    # exponent for tank surface area scaling

# Tank U-values depending on volume (W/m²·K)
TANK_U_SMALL = 1.0
TANK_U_MEDIUM = 0.8
TANK_U_LARGE = 0.5

# Pipe heat loss
PIPE_U_DEFAULT = 1.0  # default heat transfer coefficient (W/m²·K)

# Conversion factors
KGH_TO_M3S = 1 / 1000 / 3600  # kg/h to m³/s
KW_CONVERSION = 1000           # divide by 1000 to get kW


  # ==============================
# SOLAR / SHADING CONSTANTS
# ==============================
VERTICAL_IRRADIANCE_FACTOR = 0.6   # GHI → vertical conversion
DEFAULT_SHGC = 0.6   # Solar Heat Gain Coefficient