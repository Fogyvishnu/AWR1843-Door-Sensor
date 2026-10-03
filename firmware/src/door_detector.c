/**
 * @file  door_detector.c
 * @brief Standalone Door Open/Close Detector and Event Counter Implementation
 * @version 1.3.0
 */

#include "door_detector.h"
#include <string.h>
#include <math.h>
#include <stdio.h>

/* Module Control Block */
static DoorDetector_Config_t gCfg;
static DoorDetector_Status_t gStatus;
static DoorDiagnostics_t     gDiagnostics;

/* Internal calibration accumulator */
static uint32_t gCalibSamplesCount = 0;
static float gCalibDistanceAccum = 0.0f;
static float gCalibPeakSnrAccum = 0.0f;

/* Uptime accumulator in milliseconds */
static uint32_t gUptimeAccumMs = 0;

/* Helper to record event transitions in rolling history */
static void DoorDetector_recordEvent(DoorState_e oldState, DoorState_e newState)
{
    int32_t idx;
    for (idx = (int32_t)DOOR_EVENT_HISTORY_SIZE - 1; idx > 0; idx--)
    {
        gStatus.history[idx] = gStatus.history[idx - 1];
    }
    gStatus.history[0].prevState = oldState;
    gStatus.history[0].newState = newState;
    gStatus.history[0].frameNum = gStatus.frameCount;
    gStatus.history[0].openCount = gStatus.totalOpenCount;
    gStatus.history[0].closeCount = gStatus.totalCloseCount;
    gStatus.history[0].distance = gStatus.avgDoorDistance;
    gStatus.history[0].snr = gStatus.peakSnr;
    if (gStatus.historyCount < DOOR_EVENT_HISTORY_SIZE)
    {
        gStatus.historyCount++;
    }
    gStatus.stateDurationMs = 0;
}

/* Helper to generate visual ASCII gauge bar */
static void DoorDetector_makeBar(char *bar, int barLen, float val, float maxVal)
{
    int filled;
    int i;
    if (val < 0.0f) val = 0.0f;
    if (val > maxVal) val = maxVal;
    filled = (int)((val / maxVal) * (float)barLen);
    if (filled > barLen) filled = barLen;
    for (i = 0; i < barLen; i++)
    {
        if (i < filled)
        {
            bar[i] = '=';
        }
        else if (i == filled)
        {
            bar[i] = '>';
        }
        else
        {
            bar[i] = ' ';
        }
    }
    bar[barLen] = '\0';
}

DoorResult_e DoorDetector_validateConfig(const DoorDetector_Config_t *cfg)
{
    if (cfg == NULL)
    {
        return DOOR_ERR_NULL_POINTER;
    }

    if ((cfg->rangeMin < DOOR_RANGE_MIN_LIMIT) || (cfg->rangeMax > DOOR_RANGE_MAX_LIMIT))
    {
        return DOOR_ERR_INVALID_PARAM;
    }

    if (cfg->rangeMax <= (cfg->rangeMin + 0.05f))
    {
        return DOOR_ERR_INVALID_PARAM;
    }

    if ((cfg->xMin >= cfg->xMax) || (fabsf(cfg->xMin) > DOOR_LATERAL_MAX_LIMIT) || (fabsf(cfg->xMax) > DOOR_LATERAL_MAX_LIMIT))
    {
        return DOOR_ERR_INVALID_PARAM;
    }

    if ((cfg->zMin >= cfg->zMax) || (fabsf(cfg->zMin) > DOOR_ELEVATION_MAX_LIMIT) || (fabsf(cfg->zMax) > DOOR_ELEVATION_MAX_LIMIT))
    {
        return DOOR_ERR_INVALID_PARAM;
    }

    if ((cfg->debounceOpenFrames < DOOR_MIN_DEBOUNCE_FRAMES) || (cfg->debounceOpenFrames > DOOR_MAX_DEBOUNCE_FRAMES))
    {
        return DOOR_ERR_INVALID_PARAM;
    }

    if ((cfg->debounceCloseFrames < DOOR_MIN_DEBOUNCE_FRAMES) || (cfg->debounceCloseFrames > DOOR_MAX_DEBOUNCE_FRAMES))
    {
        return DOOR_ERR_INVALID_PARAM;
    }

    if (cfg->autoCalibrate && ((cfg->calibFrameCount < 5U) || (cfg->calibFrameCount > 200U)))
    {
        return DOOR_ERR_INVALID_PARAM;
    }

    return DOOR_OK;
}

DoorResult_e DoorDetector_init(const DoorDetector_Config_t *cfg)
{
    memset(&gStatus, 0, sizeof(gStatus));
    memset(&gDiagnostics, 0, sizeof(gDiagnostics));

    gDiagnostics.healthStatus = DOOR_HEALTH_OK;
    gUptimeAccumMs = 0;

    if (cfg != NULL)
    {
        DoorResult_e res = DoorDetector_validateConfig(cfg);
        if (res != DOOR_OK)
        {
            return res;
        }
        memcpy(&gCfg, cfg, sizeof(DoorDetector_Config_t));
    }
    else
    {
        /* Factory Default configuration: sensor placed 0.4m - 1.8m facing the door */
        gCfg.rangeMin = 0.40f;              /* 40 cm min distance */
        gCfg.rangeMax = 1.80f;              /* 180 cm max distance */
        gCfg.xMin = -0.80f;                 /* +/- 80 cm width coverage */
        gCfg.xMax = 0.80f;
        gCfg.zMin = -1.00f;                 /* +/- 1.0 m elevation coverage */
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
    gStatus.vt100Mode = 1;                  /* VT100 dashboard enabled by default */
    gStatus.historyCount = 0;
    gStatus.stateDurationMs = 0;
    gCalibSamplesCount = 0;
    gCalibDistanceAccum = 0.0f;
    gCalibPeakSnrAccum = 0.0f;

    return DOOR_OK;
}

DoorResult_e DoorDetector_setConfig(const DoorDetector_Config_t *cfg)
{
    DoorResult_e res = DoorDetector_validateConfig(cfg);
    if (res == DOOR_OK)
    {
        memcpy(&gCfg, cfg, sizeof(DoorDetector_Config_t));
    }
    return res;
}

DoorResult_e DoorDetector_getConfig(DoorDetector_Config_t *cfg)
{
    if (cfg == NULL)
    {
        return DOOR_ERR_NULL_POINTER;
    }
    memcpy(cfg, &gCfg, sizeof(DoorDetector_Config_t));
    return DOOR_OK;
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
    gDiagnostics.totalFramesProcessed++;
    gDiagnostics.totalPointsAnalyzed += numPoints;

    gUptimeAccumMs += framePeriodMs;
    gDiagnostics.uptimeSeconds = gUptimeAccumMs / 1000U;

    if (numPoints > gDiagnostics.maxPointsInFrame)
    {
        gDiagnostics.maxPointsInFrame = numPoints;
    }

    /* Scan all detected points from the radar data path */
    if ((points != NULL) && (numPoints > 0))
    {
        for (i = 0; i < numPoints; i++)
        {
            float x = points[i].x;
            float y = points[i].y; /* Depth / range along sensor boresight */
            float z = points[i].z;

            /* Range from sensor: Euclidean radial distance */
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

                /* Enforce minimum SNR threshold for clutter rejection */
                if ((sideInfo == NULL) || (snrDb >= gCfg.minSnr))
                {
                    doorPointsCount++;
                    sumDistance += dist;

                    if (snrDb > maxSnr)
                    {
                        maxSnr = snrDb;
                    }
                }
            }
        }
    }

    if (maxSnr > gDiagnostics.maxObservedSnr)
    {
        gDiagnostics.maxObservedSnr = maxSnr;
    }

    gStatus.pointsInDoorZone = doorPointsCount;
    gStatus.peakSnr = maxSnr;
    if (doorPointsCount > 0)
    {
        gStatus.avgDoorDistance = sumDistance / (float)doorPointsCount;
    }
    else
    {
        gStatus.avgDoorDistance = 0.0f;
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
            /* Complete calibration if samples were acquired */
            if (gCalibSamplesCount > 0)
            {
                float calibDist = gCalibDistanceAccum / (float)gCalibSamplesCount;
                gCfg.rangeMin = (calibDist - 0.30f > DOOR_RANGE_MIN_LIMIT) ? (calibDist - 0.30f) : DOOR_RANGE_MIN_LIMIT;
                gCfg.rangeMax = calibDist + 0.35f;
                gStatus.isCalibrated = 1;
                gStatus.currentState = DOOR_STATE_CLOSED;
                gStatus.candidateState = DOOR_STATE_CLOSED;
            }
        }
        else if (gStatus.frameCount >= ((uint32_t)gCfg.calibFrameCount * 3U))
        {
            /* Fail-safe timeout: fallback to configured defaults if no points detected */
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

    gStatus.stateDurationMs += framePeriodMs;

    /* State Machine with Hysteresis & Debouncing */
    switch (gStatus.currentState)
    {
        case DOOR_STATE_UNKNOWN:
            if (gStatus.candidateState == DOOR_STATE_CLOSED)
            {
                gStatus.currentState = DOOR_STATE_CLOSED;
                gStatus.stateChangedFlag = 1;
                DoorDetector_recordEvent(DOOR_STATE_UNKNOWN, DOOR_STATE_CLOSED);
            }
            else
            {
                gStatus.currentState = DOOR_STATE_OPEN;
                gStatus.stateChangedFlag = 1;
                DoorDetector_recordEvent(DOOR_STATE_UNKNOWN, DOOR_STATE_OPEN);
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
                    DoorDetector_recordEvent(DOOR_STATE_CLOSED, DOOR_STATE_OPEN);
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
                    DoorDetector_recordEvent(DOOR_STATE_OPEN, DOOR_STATE_CLOSED);
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

DoorResult_e DoorDetector_getSnapshot(DoorDetector_Status_t *outSnapshot)
{
    if (outSnapshot == NULL)
    {
        return DOOR_ERR_NULL_POINTER;
    }
    memcpy(outSnapshot, &gStatus, sizeof(DoorDetector_Status_t));
    return DOOR_OK;
}

DoorResult_e DoorDetector_getDiagnostics(DoorDiagnostics_t *diag)
{
    if (diag == NULL)
    {
        return DOOR_ERR_NULL_POINTER;
    }
    memcpy(diag, &gDiagnostics, sizeof(DoorDiagnostics_t));
    return DOOR_OK;
}

void DoorDetector_resetCounters(void)
{
    gStatus.totalOpenCount = 0;
    gStatus.totalCloseCount = 0;
    gStatus.openDurationMs = 0;
    gStatus.stateDurationMs = 0;
    gStatus.openDebounceCounter = 0;
    gStatus.closeDebounceCounter = 0;
    gStatus.historyCount = 0;
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

void DoorDetector_setVt100Mode(uint8_t enable)
{
    gStatus.vt100Mode = enable ? 1 : 0;
}

uint8_t DoorDetector_getVt100Mode(void)
{
    return gStatus.vt100Mode;
}

#define VT100_APPEND(...) do { \
    int32_t written = snprintf(outBuf + offset, (offset < (int32_t)maxLen) ? (maxLen - offset) : 0, __VA_ARGS__); \
    if (written > 0) offset += written; \
} while(0)

uint32_t DoorDetector_formatVt100Screen(char *outBuf, uint32_t maxLen)
{
    int32_t offset = 0;
    uint32_t totalSec = gStatus.stateDurationMs / 1000U;
    uint32_t hh = totalSec / 3600U;
    uint32_t mm = (totalSec % 3600U) / 60U;
    uint32_t ss = totalSec % 60U;
    uint32_t k;
    char distBar[16];
    char snrBar[16];

    if ((outBuf == NULL) || (maxLen == 0))
    {
        return 0;
    }

    DoorDetector_makeBar(distBar, 14, gStatus.avgDoorDistance, 2.5f);
    DoorDetector_makeBar(snrBar, 14, gStatus.peakSnr, 30.0f);

    /* Move cursor to row 1, col 1 and hide cursor */
    VT100_APPEND("\x1B[H\x1B[?25l");

    /* Header */
    VT100_APPEND("\x1B[1;36m+-----------------------------------------------------------------------------+\x1B[0m\x1B[K\r\n");
    VT100_APPEND("\x1B[1;36m|      TI AWR1843BOOST mmWave Radar - Standalone Door Monitor [VT100]         |\x1B[0m\x1B[K\r\n");
    VT100_APPEND("\x1B[1;36m|         FMCW 77 GHz  |  10 Hz Telemetry  |  On-Chip Real-Time Processing    |\x1B[0m\x1B[K\r\n");
    VT100_APPEND("\x1B[1;36m+-----------------------------------------------------------------------------+\x1B[0m\x1B[K\r\n");

    /* Status Banner */
    if (gStatus.currentState == DOOR_STATE_CLOSED)
    {
        VT100_APPEND("\x1B[1;32m|  CURRENT STATUS : [  DOOR CLOSED  ]        LED DS3 : OFF (Secure)           |\x1B[0m\x1B[K\r\n");
    }
    else if (gStatus.currentState == DOOR_STATE_OPEN)
    {
        VT100_APPEND("\x1B[1;31m|  CURRENT STATUS : [   DOOR OPEN   ]        LED DS3 : ON  (Passage Active!)  |\x1B[0m\x1B[K\r\n");
    }
    else if (!gStatus.isCalibrated)
    {
        VT100_APPEND("\x1B[1;33m|  CURRENT STATUS : [ CALIBRATING... ]       Keep door closed for ~2 seconds   |\x1B[0m\x1B[K\r\n");
    }
    else
    {
        VT100_APPEND("\x1B[1;33m|  CURRENT STATUS : [    UNKNOWN    ]        Awaiting radar frame detections  |\x1B[0m\x1B[K\r\n");
    }

    /* Sub-panels: Visual Graphic & Metrics */
    VT100_APPEND("\x1B[1;36m+-------------------+---------------------------------------------------------+\x1B[0m\x1B[K\r\n");
    VT100_APPEND("\x1B[1;36m| DOOR VISUAL       | RADAR SENSING METRICS & PASSAGE STATISTICS              |\x1B[0m\x1B[K\r\n");
    VT100_APPEND("\x1B[1;36m+-------------------+---------------------------------------------------------+\x1B[0m\x1B[K\r\n");

    if (gStatus.currentState == DOOR_STATE_CLOSED)
    {
        VT100_APPEND("|   +-----------+   | Target Distance : %5.2f m   | Total Openings : %-8u |\x1B[K\r\n", gStatus.avgDoorDistance, (unsigned int)gStatus.totalOpenCount);
        VT100_APPEND("|   |   |   |   |   | Distance Gauge  : [%s] | Total Closings : %-8u |\x1B[K\r\n", distBar, (unsigned int)gStatus.totalCloseCount);
        VT100_APPEND("|   |   | . |   |   | Peak Reflection : %5.1f dB  | Time In State  : %02u:%02u:%02u |\x1B[K\r\n", gStatus.peakSnr, (unsigned int)hh, (unsigned int)mm, (unsigned int)ss);
        VT100_APPEND("|   |   |   |   |   | SNR Gauge       : [%s] | Debounce Filter: 500 ms   |\x1B[K\r\n", snrBar);
        VT100_APPEND("|   +-----------+   | Points in ROI   : %3u points | Frame Count    : %-8u |\x1B[K\r\n", (unsigned int)gStatus.pointsInDoorZone, (unsigned int)gStatus.frameCount);
        VT100_APPEND("|   [DOOR CLOSED]   | Auto-Baseline   : %-10s | Radar State    : ACTIVE   |\x1B[K\r\n", gStatus.isCalibrated ? "LOCKED (OK)" : "CALIB...");
    }
    else
    {
        VT100_APPEND("|   +           +   | Target Distance :   --- m     | Total Openings : %-8u |\x1B[K\r\n", (unsigned int)gStatus.totalOpenCount);
        VT100_APPEND("|    \\         /    | Distance Gauge  : [%s] | Total Closings : %-8u |\x1B[K\r\n", distBar, (unsigned int)gStatus.totalCloseCount);
        VT100_APPEND("|     \\   .   /     | Peak Reflection : %5.1f dB  | Time In State  : %02u:%02u:%02u |\x1B[K\r\n", gStatus.peakSnr, (unsigned int)hh, (unsigned int)mm, (unsigned int)ss);
        VT100_APPEND("|      \\     /      | SNR Gauge       : [%s] | Debounce Filter: 500 ms   |\x1B[K\r\n", snrBar);
        VT100_APPEND("|   +           +   | Points in ROI   : %3u points | Frame Count    : %-8u |\x1B[K\r\n", (unsigned int)gStatus.pointsInDoorZone, (unsigned int)gStatus.frameCount);
        VT100_APPEND("|    [DOOR OPEN]    | Auto-Baseline   : %-10s | Radar State    : ACTIVE   |\x1B[K\r\n", gStatus.isCalibrated ? "LOCKED (OK)" : "CALIB...");
    }

    /* Event History Table */
    VT100_APPEND("\x1B[1;36m+-------------------+---------------------------------------------------------+\x1B[0m\x1B[K\r\n");
    VT100_APPEND("\x1B[1;36m| RECENT EVENT TRANSITION HISTORY                                             |\x1B[0m\x1B[K\r\n");
    VT100_APPEND("\x1B[1;36m+----+-------------+--------------+--------+--------+------------+------------+\x1B[0m\x1B[K\r\n");
    VT100_APPEND("\x1B[1;36m| #  | Event       | Transition   | Opens  | Closes | Distance   | Peak SNR   |\x1B[0m\x1B[K\r\n");
    VT100_APPEND("\x1B[1;36m+----+-------------+--------------+--------+--------+------------+------------+\x1B[0m\x1B[K\r\n");

    if (gStatus.historyCount == 0)
    {
        VT100_APPEND("| -- | No state transitions recorded yet. Monitoring doorway zone...        |\x1B[K\r\n");
    }
    else
    {
        for (k = 0; k < gStatus.historyCount; k++)
        {
            const DoorEventRecord_t *rec = &gStatus.history[k];
            const char *evtStr = (rec->newState == DOOR_STATE_OPEN) ? "DOOR OPEN " : "DOOR CLOSE";
            const char *transStr = (rec->newState == DOOR_STATE_OPEN) ? "CLOSE->OPEN" : "OPEN->CLOSE";
            char distStr[16];
            if ((rec->newState == DOOR_STATE_CLOSED) && (rec->distance > 0.05f))
            {
                snprintf(distStr, sizeof(distStr), "%5.2f m", rec->distance);
            }
            else
            {
                snprintf(distStr, sizeof(distStr), "  --- m ");
            }
            VT100_APPEND("| %-2u | %-11s | %-12s | %-6u | %-6u | %-10s | %5.1f dB  |\x1B[K\r\n",
                (unsigned int)(k + 1), evtStr, transStr,
                (unsigned int)rec->openCount, (unsigned int)rec->closeCount,
                distStr, rec->snr);
        }
    }

    /* Command prompt footer */
    VT100_APPEND("\x1B[1;36m+----+-------------+--------------+--------+--------+------------+------------+\x1B[0m\x1B[K\r\n");
    VT100_APPEND("| COMMANDS: [r] Reset Counters  |  [c] Recalibrate  |  [t] Toggle VT100/Raw   |\x1B[K\r\n");
    VT100_APPEND("\x1B[1;36m+-----------------------------------------------------------------------------+\x1B[0m\x1B[K\r\n");

    if (offset >= (int32_t)maxLen)
    {
        offset = (int32_t)maxLen - 1;
        outBuf[offset] = '\0';
    }
    return (uint32_t)offset;
}
