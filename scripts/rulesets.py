#!/usr/bin/env python3
"""Generate repository rulesets; the caller decides when to apply them."""
import argparse, json

def rulesets(app_id, status, extra_statuses=()):
    admin={'actor_type':'OrganizationAdmin','bypass_mode':'always'}
    app={'actor_type':'Integration','actor_id':app_id,'bypass_mode':'always'}
    def make(name,target,refs,bypass,rules):
        return {'name':name,'target':target,'enforcement':'active','bypass_actors':bypass,'conditions':{'ref_name':{'include':refs,'exclude':[]}},'rules':rules}
    return [
        make('mc-ci: default branch','branch',['~DEFAULT_BRANCH'],[admin],[
            {'type':'pull_request','parameters':{'dismiss_stale_reviews_on_push':False,'require_code_owner_review':False,'require_last_push_approval':False,'required_approving_review_count':0,'required_review_thread_resolution':False}},
            {'type':'required_status_checks','parameters':{'strict_required_status_checks_policy':False,'required_status_checks':[{'context':name} for name in (status, *extra_statuses)]}},
            {'type':'non_fast_forward'}]),
        make('mc-ci: release tag creation','tag',['refs/tags/v*'],[admin,app],[{'type':'creation'}]),
        make('mc-ci: release tag immutability','tag',['refs/tags/v*'],[admin],[{'type':'update'},{'type':'deletion'}]),
    ]

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--app-id',required=True,type=int); parser.add_argument('--status',required=True); parser.add_argument('--extra-status',action='append',default=[])
    args=parser.parse_args()
    if args.app_id<=0 or any(not name.strip() or '\n' in name or '\r' in name for name in [args.status, *args.extra_status]): parser.error('invalid app ID or status')
    print(json.dumps(rulesets(args.app_id,args.status,args.extra_status),indent=2))
if __name__=='__main__': main()
