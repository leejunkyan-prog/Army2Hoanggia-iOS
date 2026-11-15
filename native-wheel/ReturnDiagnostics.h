#pragma once
#include <stdint.h>
enum {
    RD_OK,RD_SCREEN,RD_ROWS,RD_VISIBLE,RD_ANIMATED,RD_TRANSITION,
    RD_SELECTED,RD_SCROLL_TARGET,RD_SCROLL_CURRENT,RD_SCROLL_MAX,
    RD_DIALOG,RD_FLASH,RD_PRESSED,RD_RELEASED,RD_POINTER_DOWN,RD_POINTER_UP,
    RD_WIDTH,RD_HEIGHT,RD_ROOM,RD_FIRST_ID,RD_LAST_ID,RD_CANVAS_STEP,RD_COUNT
};
typedef struct {
    uint64_t gameTicks,renderTicks,inputEvents,blockedInputs;
    uint64_t gameAt,renderAt,inputAt,sampleAt;
    int native[RD_COUNT];
    int inputKind,softKey,inputBlocker;
} AGReturnDiagnostic;
#ifdef AG_RETURN_DIAGNOSTIC
void AGReturnPulse(int variant,int source);
void AGReturnInput(int variant,int kind,int code,int blocker);
void AGReturnInputStage(int variant,int kind,int code,int stage);
int AGReturnShouldSample(int variant);
void AGReturnPublish(int variant,const int values[RD_COUNT]);
int AGReturnDiagnosticCopy(int variant,AGReturnDiagnostic *out);
void AGReturnDiagnosticSave(void);
void AGNativeWatchReturnDiagnostic(void *env,int variant);
#else
static inline void AGReturnPulse(int v,int s){}
static inline void AGReturnInput(int v,int k,int c,int b){}
static inline void AGReturnInputStage(int v,int k,int c,int s){}
#endif
