import pypsa
from .models import NetworkResult
import os
import pypsa
from django.conf import settings

def load_latest_network(path):

    network = pypsa.Network()

    network.import_from_csv_folder(
        path
    )

    return network
def run_baseline(network):
    
    print("Running BASELINE optimization")
    # Baseline uses Power Flow
    network.pf()

    return network


# ============================================================
# SOLAR OPTIMIZATION
# ============================================================

def run_solar(network):

    print("Running SOLAR optimization")
    # Solar uses Power Flow
    network.pf()

    return network


# ============================================================
# STORAGE OPTIMIZATION
# ============================================================

def run_storage(network):

    print("Running STORAGE optimization")
    # ========================================================
    # STORAGE OPTIMIZATION
    # ========================================================
    # Run power flow
    # Define the number of snapshots and group size
    num_snapshots = len(network.snapshots)  # Get total number of snapshots
    group_size = 24  # Set group size, e.g., 24 snapshots (if each snapshot represents one hour)
    # Optimize snapshots in groups
    for i in range(int(num_snapshots / group_size)):
        snapshots_subset = network.snapshots[group_size * i : group_size * i + group_size]
        network.optimize( 
            snapshots_subset,
            solver_name="highs",
        )
    return network


# ============================================================
# SAVE OPTIMIZED NETWORK
# ============================================================

def save_optimized_network(
    network,
    network_type
):

    save_folder = os.path.join(
        settings.MEDIA_ROOT,
        "networks",
        network_type,
        "latest"
    )

    os.makedirs(
        save_folder,
        exist_ok=True
    )

    # Save PyPSA network
    network.export_to_csv_folder(
        save_folder
    )

    # Mark only this type as old
    NetworkResult.objects.filter(
        result_type=network_type
    ).update(
        is_latest=False
    )

    # Create new latest result
    result = NetworkResult.objects.create(
        name="latest",
        result_type=network_type,
        network_path=save_folder,
        is_latest=True
    )

    return result, save_folder

