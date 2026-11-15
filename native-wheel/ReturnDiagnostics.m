/* Diagnostic build: only copied scalar metadata reaches the file worker.
   No native calls, game Env, packet body, account or chat data enter UIKit. */
#import <UIKit/UIKit.h>
#include <stdatomic.h>
#include <time.h>
#include "ReturnDiagnostics.h"
#include "ThreadDiagnostics.h"
#include "CanvasRecovery.h"
#include "CraftDiagnostics.h"
#ifdef AG_RETURN_DIAGNOSTIC
static struct {
    atomic_uint_fast64_t gameTicks,renderTicks,inputEvents,blockedInputs;
    atomic_uint_fast64_t gameAt,renderAt,inputAt,sampleAt,claimedAt;
    atomic_int native[RD_COUNT],inputKind,softKey,inputBlocker;
} returns[6];
static uint64_t millis(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000+t.tv_nsec/1000000;}
void AGReturnPulse(int v,int source){
    if(v<0||v>=6)return;
    AGThreadPulse(v,source);
    if(source==0){atomic_fetch_add(&returns[v].gameTicks,1);atomic_store(&returns[v].gameAt,millis());}
    else {atomic_fetch_add(&returns[v].renderTicks,1);atomic_store(&returns[v].renderAt,millis());}
}
void AGReturnInput(int v,int kind,int code,int blocker){
    if(v<0||v>=6)return;
    atomic_fetch_add(&returns[v].inputEvents,1);
    if(blocker)atomic_fetch_add(&returns[v].blockedInputs,1);
    atomic_store(&returns[v].inputAt,millis());
    atomic_store(&returns[v].inputKind,kind);
    /* Retain only native soft keys/directions. Never log typed characters. */
    atomic_store(&returns[v].softKey,code<0&&code>=-32?code:0);
    atomic_store(&returns[v].inputBlocker,blocker);
}
void AGReturnInputStage(int v,int kind,int code,int stage){
    if(v<0||v>=6)return;
    atomic_store(&returns[v].inputAt,millis());
    atomic_store(&returns[v].inputKind,kind);
    atomic_store(&returns[v].softKey,code<0&&code>=-32?code:0);
    atomic_store(&returns[v].inputBlocker,stage);
}
int AGReturnShouldSample(int v){
    if(v<0||v>=6)return 0;
    uint64_t at=millis(),before=atomic_load(&returns[v].claimedAt);
    return at>=before+500&&atomic_compare_exchange_strong(&returns[v].claimedAt,&before,at);
}
void AGReturnPublish(int v,const int values[RD_COUNT]){
    if(v<0||v>=6||!values)return;
    for(int i=0;i<RD_COUNT;i++)atomic_store(&returns[v].native[i],values[i]);
    atomic_store(&returns[v].sampleAt,millis());
}
int AGReturnDiagnosticCopy(int v,AGReturnDiagnostic *out){
    if(v<0||v>=6||!out)return 0;
#define COPY(name) out->name=atomic_load(&returns[v].name)
    COPY(gameTicks);COPY(renderTicks);COPY(inputEvents);COPY(blockedInputs);
    COPY(gameAt);COPY(renderAt);COPY(inputAt);COPY(sampleAt);
    COPY(inputKind);COPY(softKey);COPY(inputBlocker);
#undef COPY
    for(int i=0;i<RD_COUNT;i++)out->native[i]=atomic_load(&returns[v].native[i]);
    return 1;
}
static dispatch_queue_t logQueue(void){
    static dispatch_queue_t q;static dispatch_once_t once;
    dispatch_once(&once,^{q=dispatch_queue_create("vn.army2hoanggia.return297-log",DISPATCH_QUEUE_SERIAL);});return q;
}
static NSString *directory(void){return NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;}
static NSString *stamp(void){return [[NSISO8601DateFormatter new] stringFromDate:NSDate.date];}
#ifdef AG_CRAFT_DIAGNOSTIC
static NSDictionary *craftSnapshot(int v,uint64_t at){
    AGCraftDiagnostic d={0};AGCraftDiagnosticCopy(v,&d);
    static const char *names[CF_COUNT]={"sample_ok","inventory_screen_kind","parent_depth","state_open","state_matches_root","has_private_display",
        "selected_index","display_rows","source_rows","inventory_menu_flag","amount_flag","modal_present","menu_visible","menu_index","menu_rows",
        "slot_kind","slot_id","slot_quantity","cached_kind","cached_id","cached_quantity","slot_equals_cached","source_match_found",
        "source_equals_slot","source_equals_cached","source_quantity","display_is_source","display_is_private","argument_is_slot",
        "argument_is_cached","argument_in_source","snapshot_stable"};
    NSMutableDictionary *s=[@{@"detail_calls":@(d.detailCalls),@"classifier_accepted":@(d.accepted),@"classifier_rejected":@(d.rejected),
        @"received_packets":@(d.packets),@"sample_age_ms":d.at?@(at>=d.at?at-d.at:0):@(-1)} mutableCopy];
    for(int i=0;i<CF_COUNT;i++)s[[NSString stringWithUTF8String:names[i]]]=@(d.values[i]);return s;
}
static NSArray *craftEvents(void){
    AGCraftEvent copied[AG_CRAFT_EVENTS];int count=AGCraftEventsCopy(copied,AG_CRAFT_EVENTS);
    static const char *names[CE_COUNT]={"kind","pb","command","remaining_bytes","classifier_result","classifier_reason",
        "input_kind","input_id","input_quantity","resolved_kind","resolved_id","resolved_quantity","handle_changed",
        "input_matches_selection","resolved_in_source","selected_index"};
    NSMutableArray *result=[NSMutableArray array];
    for(int n=0;n<count;n++){NSMutableDictionary *row=[@{@"uptime_ms":@(copied[n].at)} mutableCopy];
        for(int i=0;i<CE_COUNT;i++)row[[NSString stringWithUTF8String:names[i]]]=@(copied[n].values[i]);[result addObject:row];}
    return result;
}
#endif
static NSDictionary *snapshot(int v,uint64_t at){
    AGReturnDiagnostic d={0};AGReturnDiagnosticCopy(v,&d);
    static const char *names[RD_COUNT]={"sample_ok","screen_kind","area_rows","area_visible","area_animated","transition",
        "selected","scroll_target","scroll_current","scroll_max","modal_present","flash",
        "pressed_keys","released_keys","pointer_down","pointer_up","canvas_width","canvas_height",
        "area_room","first_area_id","last_area_id","canvas_sequence"};
    NSMutableDictionary *s=[@{@"pb":@(v+1),@"game_ticks":@(d.gameTicks),@"render_ticks":@(d.renderTicks),
        @"input_events":@(d.inputEvents),@"blocked_inputs":@(d.blockedInputs),@"input_kind":@(d.inputKind),
        @"soft_key":@(d.softKey),@"input_blocker":@(d.inputBlocker)} mutableCopy];
    uint64_t times[4]={d.gameAt,d.renderAt,d.inputAt,d.sampleAt};
    NSArray *ages=@[@"game_age_ms",@"render_age_ms",@"input_age_ms",@"sample_age_ms"];
    for(int i=0;i<4;i++)s[ages[i]]=times[i]?@(at>=times[i]?at-times[i]:0):@(-1);
    for(int i=0;i<RD_COUNT;i++)s[[NSString stringWithUTF8String:names[i]]]=@(d.native[i]);
#ifdef AG_CANVAS_RECOVERY
    AGCanvasRecovery recovery={0};AGCanvasRecoveryCopy(v,&recovery);
    s[@"canvas_recovery"]=@{@"attempts":@(recovery.attempts),@"recovered":@(recovery.recovered),
        @"failures":@(recovery.failures),@"armed":@(recovery.armed),@"pending":@(recovery.pending),@"status":@(recovery.status),@"target_registered":@(recovery.registered)};
#endif
#ifdef AG_CRAFT_DIAGNOSTIC
    s[@"craft"]=craftSnapshot(v,at);
#endif
    return s;
}
static void saveSnapshot(void){
    static NSMutableArray *history;static NSString *session;
    if(!history)history=[NSMutableArray array];if(!session)session=stamp();
    uint64_t at=millis();NSMutableArray *pbs=[NSMutableArray array];
    for(int v=0;v<6;v++)[pbs addObject:snapshot(v,at)];
    NSMutableArray *active=[NSMutableArray array];
    for(NSDictionary *pb in pbs)if([pb[@"game_ticks"] unsignedLongLongValue]||[pb[@"render_ticks"] unsignedLongLongValue]||[pb[@"input_events"] unsignedLongLongValue])[active addObject:pb];
    [history addObject:@{@"at":stamp(),@"uptime_ms":@(at),@"pbs":active}];
    while(history.count>180)[history removeObjectAtIndex:0];
    NSData *watchData=[NSData dataWithContentsOfFile:[directory() stringByAppendingPathComponent:[NSString stringWithFormat:@"Watch%d-watch.json",AG_RETURN_BUILD]]];
    id watch=watchData?[NSJSONSerialization JSONObjectWithData:watchData options:0 error:nil]:nil;
    NSMutableArray *windows=[NSMutableArray array];
    for(UIWindow *window in UIApplication.sharedApplication.windows){
        if(window.hidden)continue;
        NSMutableArray *children=[NSMutableArray array];
        for(UIViewController *child in window.rootViewController.childViewControllers)[children addObject:NSStringFromClass(child.class)];
        [windows addObject:@{@"class":NSStringFromClass(window.class),@"key":@(window.isKeyWindow),@"level":@(window.windowLevel),
            @"root":window.rootViewController?NSStringFromClass(window.rootViewController.class):@"none",@"children":children}];
    }
    NSDictionary *report=@{@"build":@(AG_RETURN_BUILD),@"diagnostic_revision":[NSString stringWithFormat:@"%d-native-return-state-1",AG_RETURN_BUILD],@"created_at":stamp(),
        @"session_started_at":session,@"app_build":NSBundle.mainBundle.infoDictionary[@"CFBundleVersion"]?:@"unknown",
        @"screen_kind_legend":@{@"0":@"unknown",@"1":@"area",@"2":@"arena",@"3":@"room",@"4":@"other"},
        @"input_blocker_legend":@{@"0":@"passed_to_game",@"1":@"watch",@"2":@"battlefield_lobby",@"3":@"notes_or_wheel",
            @"-1":@"inside_watch_guard",@"-2":@"inside_lobby_guard",@"-3":@"inside_notes_guard",@"-4":@"inside_wheel_guard"},
        @"latest_watch":watch?:@{},@"visible_windows":windows,@"latest":pbs,@"history":[history copy]};
    NSString *prefix=@"Watch";
#ifdef AG_CRAFT_DIAGNOSTIC
    prefix=@"Craft";
#endif
    NSString *path=[directory() stringByAppendingPathComponent:[NSString stringWithFormat:@"%@%d-diagnostic.json",prefix,AG_RETURN_BUILD]];
    if(path)dispatch_async(logQueue(),^{
        NSMutableDictionary *complete=[report mutableCopy];
#ifdef AG_RETURN_THREAD_DIAGNOSTIC
        complete[@"thread_samples"]=AGThreadDiagnosticsSample();
        complete[@"thread_sampling"] = @"this_process_only; no thread suspension; image-relative code locations; waiting=3, running=1";
#endif
#ifdef AG_CRAFT_DIAGNOSTIC
        complete[@"diagnostic_revision"]=@"300-craft-detail-state-1";
        complete[@"craft_events"]=craftEvents();
        complete[@"craft_legend"]=@{@"screen_kind":@{@"0":@"outside_inventory",@"1":@"inventory",@"2":@"inventory_child"},
            @"event_kind":@{@"1":@"detail_classifier",@"2":@"receive_before_native_dispatch"},
            @"item_kind":@{@"0":@"absent",@"1":@"equipment_uid_omitted",@"2":@"consumable_template"},
            @"classifier_reason":@{@"0":@"invalid_input",@"1":@"not_consumable",@"2":@"known_recipe_id",@"3":@"no_description",@"4":@"short_description",@"5":@"prefix_mismatch",@"6":@"prefix_match",@"7":@"string_unavailable",@"8":@"native_exception"},
            @"classifier_result":@"Client recognition only, not server craft success. Incoming payloads and item description text are omitted."};
#endif
        NSData *data=[NSJSONSerialization dataWithJSONObject:complete options:NSJSONWritingPrettyPrinted error:nil];
        if(data)[data writeToFile:path atomically:YES];
    });
}
void AGReturnDiagnosticSave(void){saveSnapshot();dispatch_sync(logQueue(),^{});}
__attribute__((constructor)) static void installReturnDiagnostics(void){
    dispatch_async(dispatch_get_main_queue(),^{
        [NSTimer scheduledTimerWithTimeInterval:1 repeats:YES block:^(NSTimer *timer){saveSnapshot();}];
        [NSNotificationCenter.defaultCenter addObserverForName:UIApplicationWillResignActiveNotification object:nil queue:NSOperationQueue.mainQueue usingBlock:^(NSNotification *n){saveSnapshot();}];
    });
}
#endif
