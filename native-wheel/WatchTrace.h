#pragma once
#include <stdint.h>
typedef struct {
    uint64_t frames,packets,exceptions,waits,expirations;
    int command,operation,waitKind,waitActor,waitStage;
    char exception[512];
} AGWatchTrace;
void AGNativeWatchTraceReset(int variant);
void AGNativeWatchTraceFrame(int variant);
void AGNativeWatchTracePacket(int variant,int command,int operation);
void AGNativeWatchTraceWait(int variant,int kind,int actor,int stage);
int AGNativeWatchTraceCopy(int variant,AGWatchTrace *out);
void AGNativeWatchTraceRender(int variant,int stage);
int AGNativeWatchTraceRenderCopy(int variant,uint64_t out[5]);
__attribute__((visibility("default"))) void AGNativeWatchTraceException(void *env,void *exception,int variant);
