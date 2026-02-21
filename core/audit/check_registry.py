# core/check_registry.py
from checks.aggregates import (check_avg, check_max, check_min, check_sum,
                               check_variance)
from checks.mappings import check_mappings
from checks.relationships import check_links
from checks.volume import check_volume

# Central registry of all check types
CHECK_REGISTRY = {
    "volume": [check_volume],
    "aggregates": [check_sum, check_avg, check_max, check_min, check_variance],
    "mappings": [check_mappings],  # Will run once per mapping in config
    "relationships": [check_links],  # Will run once per relation in config
    # Add more types as needed
}
