import argparse,json
p=argparse.ArgumentParser(prog='dalildz');s=p.add_subparsers(dest='cmd');s.add_parser('doctor');v=s.add_parser('verify');v.add_argument('--name');v.add_argument('--rc');a=p.parse_args()
if a.cmd=='doctor':print(json.dumps({'dalildz':'1.0.0','status':'ok'}))
elif a.cmd=='verify':print(json.dumps({'name':a.name,'rc':a.rc,'status':'NOT_VERIFIABLE','reason':'No evidence supplied'}))
