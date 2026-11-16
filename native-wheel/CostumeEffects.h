#pragma once
#include <stddef.h>
#include <stdint.h>
int AGCostumeStyleLookup(int hero,int head,int fallback);
int AGCostumeCatalog(int variant,const uint8_t *data,size_t length);
uint32_t AGCostumeTint(uint32_t rgba,uint32_t primary,uint32_t secondary);
int AGCostumeExpandRGBA(int hero,const uint8_t *source,int width,int height,int minStyle,uint8_t **out,int *outHeight);
void AGCostumeTick(void *env,int variant);
void AGCostumePaint(void *env,uint8_t *actor,int variant);
void AGCostumeObserve(void *message,int variant);
int AGCostumeSheetPalette(int hero,int style,const uint8_t *rgba,int width,int height,uint32_t *primary,uint32_t *secondary);
void AGCostumeRender(void *env,int variant);
void *AGCostumeImage(void *env,void *source,void *sheet,int hero,int style,int frames);
