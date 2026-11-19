"""Immutable protocol parameters and integer-only schedules for the disposable tSAMV devnet."""
UNIT = 1_000_000
CAP = 10_000_000_000 * UNIT
INITIAL = 6_500_000_000 * UNIT
RESERVE = 3_500_000_000 * UNIT
ERA_BLOCKS = 1_051_200
INITIAL_SUBSIDY = RESERVE // (2 * ERA_BLOCKS)

def _i(x, minimum=0):
    if type(x) is not int or x < minimum: raise ValueError("expected integer")
    return x

def default_config(profile='devnet'):
    if profile not in ('devnet','rules'): raise ValueError('unknown profile')
    short = profile == 'devnet'
    c = {'profile':profile, 'network':'tSAMV', 'network_id':('samanvay-local-devnet-v4' if short else 'samanvay-local-rules-v4'),
         'unit':UNIT,'cap':CAP,'initial':INITIAL,'reserve':RESERVE,'era_blocks':ERA_BLOCKS,
         'initial_subsidy':INITIAL_SUBSIDY,'epoch_blocks':12 if short else 720,'maturity':3 if short else 100,
         'active_epochs':7,'unbond_epochs':7,'vesting_cliff':20 if short else 262800,
         'vesting_period':80 if short else 1051200,'founder_bonus_maturity':20 if short else 262800,
         'target':(1<<248)-1,'target_spacing':1 if short else 600,
         'retarget_interval':12 if short else 2016,'max_adjustment_factor':4,
         'max_block_bytes':1_000_000,'max_transactions':1000,'max_tx_bytes':100_000,
         'future_seconds':7200,'max_expiry':10000,'max_accounts':4096,'max_locks':512,
         'max_claims':4096,'max_epochs':1024,'max_blocks':10000,
         'max_pending':20000,'max_state_bytes':8*1024*1024}
    return c

def subsidy(h,c):
    _i(h,1); e=(h-1)//c['era_blocks']; return 0 if e>=c['initial_subsidy'].bit_length() else c['initial_subsidy'] >> e

def cumulative(h,c):
    _i(h); full,part=divmod(h,c['era_blocks']); lim=c['initial_subsidy'].bit_length()
    return c['era_blocks']*sum(c['initial_subsidy']>>e for e in range(min(full,lim))) + (part*(c['initial_subsidy']>>full) if full<lim else 0)

def split(h,c):
    _i(h,1); now,old=cumulative(h,c),cumulative(h-1,c); f,fo=now//10,old//10; n,no=4*now//10,4*old//10
    return {'miner':now-old-((n-f)-(no-fo))-(f-fo),'staking':(n-f)-(no-fo),'founder':f-fo}

def epoch_of(h,c): _i(h,1); return (h-1)//c['epoch_blocks']
def epoch_start(e,c): _i(e); return e*c['epoch_blocks']+1
def epoch_end(e,c): return epoch_start(e,c)+c['epoch_blocks']-1
def activation_height(h,c): return epoch_start(epoch_of(h,c)+1,c)
def exit_effective_height(lock_h, request_h, c):
    _i(lock_h,1); _i(request_h,1)
    earliest=activation_height(lock_h,c)+c['active_epochs']*c['epoch_blocks']
    if request_h < lock_h or request_h < earliest-c['epoch_blocks']:
        raise ValueError('exit request too early')
    return max(activation_height(request_h,c), earliest)
def withdraw_height(exit_h,c):
    _i(exit_h,1)
    if (exit_h-1)%c['epoch_blocks']: raise ValueError('exit must be epoch boundary')
    return exit_h+c['unbond_epochs']*c['epoch_blocks']
def claim_height(e,c): _i(e); return epoch_end(e,c)+c['maturity']
def epoch_budget(e,c):
    a,b=cumulative(epoch_end(e,c),c),cumulative(epoch_start(e,c)-1,c)
    return (4*a//10-a//10)-(4*b//10-b//10)
