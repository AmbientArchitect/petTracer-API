from pprint import pprint
from pettracer import get_ccs_status, login, get_ccinfo

login_res = login("richard@egilius.net", "#3ckNPH6ytGS")
print(login_res)

# Use explicit token and session when calling get_ccs_status
devices = get_ccs_status(token=login_res['token'], session=login_res['session'])
for d in devices:
    print(d.id, d.details.name, d.lastPos.posLat)

info = get_ccinfo(payload=d.id, token=login_res['token'])
pprint(info)
