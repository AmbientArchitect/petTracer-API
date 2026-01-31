"""pettracer client package"""

""" Version 0.2.0 moved to non-blocking calls and added type hints """

__version__ = "0.2.0"

from .client import (
    get_ccs_status,
    get_ccinfo,
    get_ccpositions,
    login,
    get_user_profile,
    PetTracerClient,
    PetTracerDevice,
    PetTracerError,
)
from .types import Device, MasterHs, LastPos, Details, UserProfile, LoginInfo, SubscriptionInfo

__all__ = [
    "get_ccs_status",
    "get_ccinfo",
    "get_ccpositions",
    "login",
    "get_user_profile",
    "PetTracerClient",
    "PetTracerDevice",
    "PetTracerError",
    "Device",
    "MasterHs",
    "LastPos",
    "Details",
    "UserProfile",
    "LoginInfo",
    "SubscriptionInfo",
]
