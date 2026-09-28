/**
 * @file  door_detector.c
 * @brief Standalone Door Open/Close Detector and Event Counter Implementation
 */

#include "door_detector.h"
#include <string.h>
#include <math.h>

/* Module Control Block */
static DoorDetector_Config_t gCfg;
static DoorDetector_Status_t gStatus;

/* Internal calibration accumulator */
static uint32_t gCalibSamplesCount = 0;
static float gCalibDistanceAccum = 0.0f;
static float gCalibPeakSnrAccum = 0.0f;

void DoorDetector_init(const DoorDetector_Config_t *cfg)
{
    memset(&gStatus, 0, sizeof(gStatus));

    if (cfg != NULL)
    {
        memcpy(&gCfg, cfg, sizeof(DoorDetector_Config_t));
    }
    else
    {
        /* Default configuration: sensor placed 0.5m - 1.5m facing the door */
        gCfg.rangeMin = 0.40f;              /* 40 cm min distance */
        gCfg.rangeMax = 1.80f;              /* 180 cm max distance */
        gCfg.xMin = -0.80f;                 /* +/- 80 cm width coverage */
        gCfg.xMax = 0.80f;
        gCfg.zMin = -1.00f;
        gCfg.zMax = 1.00f;
        gCfg.minPoints = 1;                 /* At least 1 CFAR detection point in zone */
        gCfg.minSnr = 10.0f;                /* 10 dB min SNR */
        gCfg.debounceOpenFrames = 5;        /* 5 frames = ~500 ms at 10 fps */
        gCfg.debounceCloseFrames = 5;       /* 5 frames = ~500 ms at 10 fps */
        gCfg.autoCalibrate = 1;             /* Auto calibrate closed door distance */
        gCfg.calibFrameCount = 20;          /* 20 frames = ~2.0 seconds */
    }

    gStatus.currentState = DOOR_STATE_UNKNOWN;
    gStatus.candidateState = DOOR_STATE_UNKNOWN;
    gStatus.isCalibrated = (gCfg.autoCalibrate == 0) ? 1 : 0;
    gCalibSamplesCount = 0;
    gCalibDistanceAccum = 0.0f;
    gCalibPeakSnrAccum = 0.0f;
}

void DoorDetector_processFrame(
    const DoorPoint_t *points,
    const DoorPointSideInfo_t *sideInfo,
    uint32_t numPoints,
    uint32_t framePeriodMs
)
{
    uint32_t i;
    uint16_t doorPointsCount = 0;
    float sumDistance = 0.0f;
    float maxSnr = 0.0f;

    gStatus.frameCount++;
    gStatus.stateChangedFlag = 0;

    /* Scan all detected points from the radar data path */
    for (i = 0; i < numPoints; i++)
    {
        float x = points[i].x;
        float y = points[i].y; /* Depth / range along sensor boresight */
        float z = points[i].z;

        /* Range from sensor: sqrt(x^2 + y^2 + z^2) or radial distance */
        float dist = sqrtf(x * x + y * y + z * z);

        /* Check if point falls inside configured Door Region of Interest (ROI) */
        if ((dist >= gCfg.rangeMin) && (dist <= gCfg.rangeMax) &&
            (x >= gCfg.xMin) && (x <= gCfg.xMax) &&
            (z >= gCfg.zMin) && (z <= gCfg.zMax))
        {
            float snrDb = 0.0f;
            if (sideInfo != NULL)
            {
                snrDb = (float)sideInfo[i].snr * 0.1f;
            }

            doorPointsCount++;
            sumDistance += dist;

            if (snrDb > maxSnr)
            {
                maxSnr = snrDb;
            }
        }
    }

    gStatus.pointsInDoorZone = doorPointsCount;
    gStatus.peakSnr = maxSnr;
    if (doorPointsCount > 0)
    {
        gStatus.avgDoorDistance = sumDistance / (float)doorPointsCount;
    }

    /* Auto-Calibration phase on boot */
    if (gCfg.autoCalibrate && !gStatus.isCalibrated)
    {
        if (doorPointsCount > 0)
        {
            gCalibDistanceAccum += gStatus.avgDoorDistance;
            gCalibPeakSnrAccum += maxSnr;
            gCalibSamplesCount++;
        }

        if (gCalibSamplesCount >= gCfg.calibFrameCount)
        {
            /* Complete calibration */
            float calibDist = gCalibDistanceAccum / (float)gCalibSamplesCount;
            gCfg.rangeMin = (calibDist - 0.30f > 0.15f) ? (calibDist - 0.30f) : 0.15f;
            gCfg.rangeMax = calibDist + 0.35f;
            gStatus.isCalibrated = 1;
            gStatus.currentState = DOOR_STATE_CLOSED;
            gStatus.candidateState = DOOR_STATE_CLOSED;
        }
        return;
    }

    /* Evaluate raw frame candidate state */
    if (doorPointsCount >= gCfg.minPoints)
    {
        gStatus.candidateState = DOOR_STATE_CLOSED;
    }
    else
    {
        gStatus.candidateState = DOOR_STATE_OPEN;
    }

    /* State Machine with Hysteresis & Debouncing */
    switch (gStatus.currentState)
    {
        case DOOR_STATE_UNKNOWN:
            if (gStatus.candidateState == DOOR_STATE_CLOSED)
            {
                gStatus.currentState = DOOR_STATE_CLOSED;
                gStatus.stateChangedFlag = 1;
            }
            else
            {
                gStatus.currentState = DOOR_STATE_OPEN;
                gStatus.stateChangedFlag = 1;
            }
            gStatus.openDebounceCounter = 0;
            gStatus.closeDebounceCounter = 0;
            break;

        case DOOR_STATE_CLOSED:
            if (gStatus.candidateState == DOOR_STATE_OPEN)
            {
                gStatus.openDebounceCounter++;
                gStatus.closeDebounceCounter = 0;

                if (gStatus.openDebounceCounter >= gCfg.debounceOpenFrames)
                {
                    gStatus.currentState = DOOR_STATE_OPEN;
                    gStatus.totalOpenCount++;
                    gStatus.stateChangedFlag = 1;
                    gStatus.openDurationMs = 0;
                    gStatus.openDebounceCounter = 0;
                }
            }
            else
            {
                /* Reset counter if door presence seen again */
                gStatus.openDebounceCounter = 0;
            }
            break;

        case DOOR_STATE_OPEN:
            gStatus.openDurationMs += framePeriodMs;

            if (gStatus.candidateState == DOOR_STATE_CLOSED)
            {
                gStatus.closeDebounceCounter++;
                gStatus.openDebounceCounter = 0;

                if (gStatus.closeDebounceCounter >= gCfg.debounceCloseFrames)
                {
                    gStatus.currentState = DOOR_STATE_CLOSED;
                    gStatus.totalCloseCount++;
                    gStatus.stateChangedFlag = 1;
                    gStatus.closeDebounceCounter = 0;
                }
            }
            else
            {
                /* Reset counter if door remains absent */
                gStatus.closeDebounceCounter = 0;
            }
            break;

        default:
            gStatus.currentState = DOOR_STATE_UNKNOWN;
            break;
    }
}

const DoorDetector_Status_t* DoorDetector_getStatus(void)
{
    return &gStatus;
}

void DoorDetector_resetCounters(void)
{
    gStatus.totalOpenCount = 0;
    gStatus.totalCloseCount = 0;
    gStatus.openDurationMs = 0;
    gStatus.openDebounceCounter = 0;
    gStatus.closeDebounceCounter = 0;
}

void DoorDetector_triggerCalibration(void)
{
    gStatus.isCalibrated = 0;
    gCalibSamplesCount = 0;
    gCalibDistanceAccum = 0.0f;
    gCalibPeakSnrAccum = 0.0f;
}

const char* DoorDetector_stateToString(DoorState_e state)
{
    switch (state)
    {
        case DOOR_STATE_CLOSED:  return "CLOSED";
        case DOOR_STATE_OPENING: return "OPENING";
        case DOOR_STATE_OPEN:    return "OPEN";
        case DOOR_STATE_CLOSING: return "CLOSING";
        default:                 return "UNKNOWN";
    }
}
