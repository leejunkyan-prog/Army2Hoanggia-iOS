#pragma once
#include <stddef.h>
#include <stdint.h>
enum { AGHUDTextLimit=32767, AGHUDSlots=128 };
typedef struct {int kind,slot,rank,maximum,seconds;size_t length;uint16_t text[AGHUDTextLimit+1];} AGHUDPacket;
int AGHUDParse(int command,const uint8_t *data,size_t size,AGHUDPacket *out);
uint32_t AGRankPixel(uint32_t argb,int rank,int fire);
int AGRankColor(int rank);
int AGHUDReceive(void *env,void *message,int variant);
int AGRankPaintActor(void *env,uint8_t *actor,uint8_t *graphics,int variant,void (*paint)(void *,void *,void *));
void *AGRankImage(void *env,void *source,int rank,int width,int height);
