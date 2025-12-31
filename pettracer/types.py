from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


def _parse_datetime(s: Optional[str]) -> Optional[datetime]:
    if s is None:
        return None
    # Expected format like: 2025-12-27T21:51:40.310+0000
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f%z")
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")
        except Exception:
            return None


@dataclass
class MasterHs:
    id: Optional[int]
    posLat: Optional[float]
    posLong: Optional[float]
    hw: Optional[int]
    sw: Optional[int]
    bl: Optional[int]
    bat: Optional[int]
    userId: Optional[int]
    status: Optional[int]
    lastContact: Optional[datetime]
    devMode: Optional[bool]

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]):
        if d is None:
            return None
        return cls(
            id=d.get("id"),
            posLat=d.get("posLat"),
            posLong=d.get("posLong"),
            hw=d.get("hw"),
            sw=d.get("sw"),
            bl=d.get("bl"),
            bat=d.get("bat"),
            userId=d.get("userId"),
            status=d.get("status"),
            lastContact=_parse_datetime(d.get("lastContact")),
            devMode=d.get("devMode"),
        )


@dataclass
class LastPos:
    id: Optional[int]
    posLat: Optional[float]
    posLong: Optional[float]
    fixS: Optional[int]
    fixP: Optional[int]
    horiPrec: Optional[int]
    sat: Optional[int]
    rssi: Optional[int]
    acc: Optional[int]
    flags: Optional[int]
    timeMeasure: Optional[datetime]
    timeDb: Optional[datetime]

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]):
        if d is None:
            return None
        return cls(
            id=d.get("id"),
            posLat=d.get("posLat"),
            posLong=d.get("posLong"),
            fixS=d.get("fixS"),
            fixP=d.get("fixP"),
            horiPrec=d.get("horiPrec"),
            sat=d.get("sat"),
            rssi=d.get("rssi"),
            acc=d.get("acc"),
            flags=d.get("flags"),
            timeMeasure=_parse_datetime(d.get("timeMeasure")),
            timeDb=_parse_datetime(d.get("timeDb")),
        )


@dataclass
class Details:
    id: Optional[int]
    image: Optional[str]
    img: Optional[str]
    color: Optional[int]
    birth: Optional[datetime]
    name: Optional[str]

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]):
        if d is None:
            return None
        return cls(
            id=d.get("id"),
            image=d.get("image"),
            img=d.get("img"),
            color=d.get("color"),
            birth=_parse_datetime(d.get("birth")),
            name=d.get("name"),
        )


@dataclass

@dataclass
class TelegramPacket:
    id: Optional[int]


@dataclass
class UserProfile:
    id: Optional[int]
    email: Optional[str]
    street: Optional[str]
    street2: Optional[str]
    zip: Optional[str]
    city: Optional[str]
    name: Optional[str]
    mobile: Optional[str]
    lang: Optional[str]
    country_id: Optional[int]
    title: Optional[str]
    image_1920: Optional[str]
    x_studio_newsletter: Optional[bool]

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]):
        if d is None:
            return None
        return cls(
            id=d.get("id"),
            email=d.get("email"),
            street=d.get("street"),
            street2=d.get("street2"),
            zip=d.get("zip"),
            city=d.get("city"),
            name=d.get("name"),
            mobile=d.get("mobile"),
            lang=d.get("lang"),
            country_id=d.get("country_id"),
            title=d.get("title"),
            image_1920=d.get("image_1920"),
            x_studio_newsletter=d.get("x_studio_newsletter"),
        )


@dataclass
class TelegramPacket:
    id: Optional[int]
    deviceType: Optional[int]
    deviceId: Optional[int]
    hsId: Optional[int]
    telegram: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    timeDb: Optional[datetime]
    timeDev: Optional[datetime]
    cmd: Optional[int]
    charging: Optional[bool]

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]):
        if d is None:
            return None
        return cls(
            id=d.get("id"),
            deviceType=d.get("deviceType"),
            deviceId=d.get("deviceId"),
            hsId=d.get("hsId"),
            telegram=d.get("telegram"),
            latitude=d.get("latitude"),
            longitude=d.get("longitude"),
            timeDb=_parse_datetime(d.get("timeDb")),
            timeDev=_parse_datetime(d.get("timeDev")),
            cmd=d.get("cmd"),
            charging=d.get("charging"),
        )


@dataclass
class ReceivedBy:
    hsId: Optional[int]
    rssi: Optional[int]

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]):
        if d is None:
            return None
        return cls(hsId=d.get("hsId"), rssi=d.get("rssi"))


@dataclass
class FifoEntry:
    telegram: Optional[TelegramPacket]
    receivedBy: Optional[List[ReceivedBy]]

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]):
        if d is None:
            return None
        return cls(
            telegram=TelegramPacket.from_dict(d.get("telegram")),
            receivedBy=[ReceivedBy.from_dict(r) for r in d.get("receivedBy", [])],
        )


@dataclass
class Device:
    id: int
    accuWarn: Optional[int]
    safetyZone: Optional[bool]
    hw: Optional[int]
    sw: Optional[int]
    bl: Optional[int]
    bat: Optional[int]
    chg: Optional[int]
    userId: Optional[int]
    masterHs: Optional[MasterHs]
    mode: Optional[int]
    modeSet: Optional[int]
    status: Optional[int]
    search: Optional[bool]
    lastTlgNr: Optional[int]
    lastContact: Optional[datetime]
    lastPos: Optional[LastPos]
    devMode: Optional[bool]
    details: Optional[Details]
    led: Optional[bool]
    ble: Optional[bool]
    buz: Optional[bool]
    lastRssi: Optional[int]
    flags: Optional[int]
    searchModeDuration: Optional[int]
    masterStatus: Optional[str]
    home: Optional[bool]
    homeSince: Optional[datetime]
    owner: Optional[bool]
    fiFo: Optional[List[FifoEntry]]

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        return cls(
            id=d["id"],
            accuWarn=d.get("accuWarn"),
            safetyZone=d.get("safetyZone"),
            hw=d.get("hw"),
            sw=d.get("sw"),
            bl=d.get("bl"),
            bat=d.get("bat"),
            chg=d.get("chg"),
            userId=d.get("userId"),
            masterHs=MasterHs.from_dict(d.get("masterHs")),
            mode=d.get("mode"),
            modeSet=d.get("modeSet"),
            status=d.get("status"),
            search=d.get("search"),
            lastTlgNr=d.get("lastTlgNr"),
            lastContact=_parse_datetime(d.get("lastContact")),
            lastPos=LastPos.from_dict(d.get("lastPos")),
            devMode=d.get("devMode"),
            details=Details.from_dict(d.get("details")),
            led=d.get("led"),
            ble=d.get("ble"),
            buz=d.get("buz"),
            lastRssi=d.get("lastRssi"),
            flags=d.get("flags"),
            searchModeDuration=d.get("searchModeDuration"),
            masterStatus=d.get("masterStatus"),
            home=d.get("home"),
            homeSince=_parse_datetime(d.get("homeSince")),
            owner=d.get("owner"),
            fiFo=[FifoEntry.from_dict(f) for f in d.get("fiFo", [])],
        )
