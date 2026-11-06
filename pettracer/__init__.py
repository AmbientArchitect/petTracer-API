"""pettracer client package"""

""" Version 0.2.0 moved to non-blocking calls and added type hints """

__version__ = "0.2.0"

from .client import (
    get_ccs_status,
    get_ccinfo,
    get_ccpositions,
    login,
    get_user_profile,
    get_home_stations,
    set_cc_mode,
    set_cc_led,
    set_cc_buz,
    PetTracerClient,
    PetTracerDevice,
    PetTracerError,
)
from .types import Device, MasterHs, HomeStation, LastPos, Details, UserProfile, LoginInfo, SubscriptionInfo, TrackingMode
from .stream import PetTracerStream, PetTracerStreamError

__all__ = [
    "get_ccs_status",
    "get_ccinfo",
    "get_ccpositions",
    "login",
    "get_user_profile",
    "get_home_stations",
    "set_cc_mode",
    "set_cc_led",
    "set_cc_buz",
    "PetTracerClient",
    "PetTracerDevice",
    "PetTracerError",
    "Device",
    "MasterHs",
    "HomeStation",
    "LastPos",
    "Details",
    "UserProfile",
    "LoginInfo",
    "SubscriptionInfo",
    "TrackingMode",
    "PetTracerStream",
    "PetTracerStreamError",
]
