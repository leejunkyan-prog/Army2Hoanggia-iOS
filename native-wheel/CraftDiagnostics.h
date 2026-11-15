#pragma once
#include <stdint.h>
enum {
    CF_OK,CF_SCREEN,CF_PARENT_DEPTH,CF_STATE_OPEN,CF_STATE_MATCH,CF_PRIVATE_DISPLAY,
    CF_SELECTED,CF_DISPLAY_COUNT,CF_SOURCE_COUNT,CF_MENU_FLAG,CF_AMOUNT_FLAG,
    CF_MODAL,CF_MENU_VISIBLE,CF_MENU_INDEX,CF_MENU_COUNT,
    CF_SLOT_KIND,CF_SLOT_ID,CF_SLOT_QUANTITY,CF_CACHE_KIND,CF_CACHE_ID,CF_CACHE_QUANTITY,
    CF_SLOT_EQUALS_CACHE,CF_SOURCE_FOUND,CF_SOURCE_EQUALS_SLOT,CF_SOURCE_EQUALS_CACHE,
    CF_SOURCE_QUANTITY,CF_DISPLAY_IS_SOURCE,CF_DISPLAY_IS_PRIVATE,CF_OPAQUE_IS_SLOT,
    CF_OPAQUE_IS_CACHE,CF_OPAQUE_IN_SOURCE,CF_SNAPSHOT_STABLE,
    CF_SINGLETON_MATCH,CF_RECIPE_ROWS,CF_RECIPE_INDEX,CF_RECIPE_PARENT_MATCH,CF_COUNT
};
enum {
    CE_KIND,CE_PB,CE_COMMAND,CE_LENGTH,CE_RESULT,CE_REASON,
    CE_INPUT_KIND,CE_INPUT_ID,CE_INPUT_QUANTITY,CE_OUTPUT_KIND,CE_OUTPUT_ID,CE_OUTPUT_QUANTITY,
    CE_HANDLE_CHANGED,CE_INPUT_SELECTED,CE_OUTPUT_IN_SOURCE,CE_SELECTED,
    CE_BIND_BEFORE,CE_BIND_AFTER,CE_BIND_STATUS,CE_COUNT
};
enum {CR_INVALID,CR_NOT_CONSUMABLE,CR_KNOWN_RECIPE,CR_NO_DESCRIPTION,CR_SHORT_DESCRIPTION,
    CR_PREFIX_MISMATCH,CR_PREFIX_MATCH,CR_STRING_UNAVAILABLE,CR_EXCEPTION};
typedef struct {uint64_t at,detailCalls,accepted,rejected,packets;int64_t values[CF_COUNT];} AGCraftDiagnostic;
typedef struct {uint64_t at;int64_t values[CE_COUNT];} AGCraftEvent;
#define AG_CRAFT_EVENTS 128
#ifdef AG_CRAFT_DIAGNOSTIC
void AGCraftSample(void *env,int variant);
void AGCraftPublish(int variant,const int64_t values[CF_COUNT]);
void AGCraftDetail(void *env,void *original,void *resolved,int result,int reason);
void AGCraftReceive(void *message,int variant);
void AGCraftRecipeBinding(int variant,int status,int before,int after);
int AGCraftDiagnosticCopy(int variant,AGCraftDiagnostic *out);
int AGCraftEventsCopy(AGCraftEvent *out,int capacity);
/* Native game memory is read only on existing attached native callbacks. */
int AGInventoryCraftInspect(int variant,void *opaque,int64_t values[CF_COUNT]);
#else
static inline void AGCraftSample(void *e,int v){}
static inline void AGCraftDetail(void *e,void *a,void *b,int r,int why){}
static inline void AGCraftReceive(void *m,int v){}
static inline void AGCraftRecipeBinding(int v,int status,int before,int after){}
#endif
