/**
 * @file  test_door_detector.c
 * @brief Production Unit Test Suite for Door Detector Module
 *
 * Can be compiled standalone on host platforms (Linux / macOS / Windows)
 * or run in automated CI/CD pipelines to verify core algorithm behavior.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <math.h>

#include "../src/door_detector.h"

/* Test Counter Macros */
static int s_testsPassed = 0;
static int s_testsFailed = 0;

#define TEST_ASSERT(cond, msg) do { \
    if (!(cond)) { \
        printf("  [FAIL] %s:%d: %s\n", __FILE__, __LINE__, msg); \
        s_testsFailed++; \
        return; \
    } \
} while(0)

#define TEST_PASS(name) do { \
    printf("  [PASS] %s\n", name); \
    s_testsPassed++; \
} while(0)

/* -------------------------------------------------------------------------
 * Test 1: Default Initialization and Validation
 * ------------------------------------------------------------------------- */
static void test_init_default_and_validation(void)
{
    DoorResult_e res;
    DoorDetector_Config_t cfg;
    const DoorDetector_Status_t *status;

    res = DoorDetector_init(NULL);
    TEST_ASSERT(res == DOOR_OK, "DoorDetector_init(NULL) should return DOOR_OK");

    res = DoorDetector_getConfig(&cfg);
    TEST_ASSERT(res == DOOR_OK, "DoorDetector_getConfig should return DOOR_OK");
    TEST_ASSERT(cfg.rangeMin == 0.40f, "Default rangeMin should be 0.40m");
    TEST_ASSERT(cfg.rangeMax == 1.80f, "Default rangeMax should be 1.80m");
    TEST_ASSERT(cfg.minSnr == 10.0f, "Default minSnr should be 10.0dB");
    TEST_ASSERT(cfg.debounceOpenFrames == 5, "Default debounceOpenFrames should be 5");

    status = DoorDetector_getStatus();
    TEST_ASSERT(status != NULL, "Status pointer should not be NULL");
    TEST_ASSERT(status->currentState == DOOR_STATE_UNKNOWN, "Initial state should be UNKNOWN");
    TEST_ASSERT(status->totalOpenCount == 0, "Initial open count should be 0");
    TEST_ASSERT(status->totalCloseCount == 0, "Initial close count should be 0");

    TEST_PASS("Default Initialization and Config Validation");
}

/* -------------------------------------------------------------------------
 * Test 2: Invalid Parameter Rejection
 * ------------------------------------------------------------------------- */
static void test_invalid_parameters(void)
{
    DoorResult_e res;
    DoorDetector_Config_t badCfg;

    /* NULL check */
    res = DoorDetector_validateConfig(NULL);
    TEST_ASSERT(res == DOOR_ERR_NULL_POINTER, "Validating NULL config should fail with NULL_POINTER");

    /* Inverted range */
    DoorDetector_getConfig(&badCfg);
    badCfg.rangeMin = 2.0f;
    badCfg.rangeMax = 1.0f;
    res = DoorDetector_validateConfig(&badCfg);
    TEST_ASSERT(res == DOOR_ERR_INVALID_PARAM, "Inverted rangeMin > rangeMax should fail");

    /* Out of bounds range */
    DoorDetector_getConfig(&badCfg);
    badCfg.rangeMax = 10.0f; /* Limit is 5.0m */
    res = DoorDetector_validateConfig(&badCfg);
    TEST_ASSERT(res == DOOR_ERR_INVALID_PARAM, "rangeMax > 5.0m should fail");

    /* Inverted X */
    DoorDetector_getConfig(&badCfg);
    badCfg.xMin = 1.0f;
    badCfg.xMax = -1.0f;
    res = DoorDetector_validateConfig(&badCfg);
    TEST_ASSERT(res == DOOR_ERR_INVALID_PARAM, "Inverted xMin > xMax should fail");

    /* Excessive debounce */
    DoorDetector_getConfig(&badCfg);
    badCfg.debounceOpenFrames = 250;
    res = DoorDetector_validateConfig(&badCfg);
    TEST_ASSERT(res == DOOR_ERR_INVALID_PARAM, "Debounce > 100 frames should fail");

    TEST_PASS("Invalid Parameter Boundary Rejection");
}

/* -------------------------------------------------------------------------
 * Test 3: 3D Spatial Gating (Inside vs Outside ROI)
 * ------------------------------------------------------------------------- */
static void test_spatial_gating_boundaries(void)
{
    DoorDetector_Config_t cfg;
    DoorPoint_t pts[4];
    DoorPointSideInfo_t info[4];
    const DoorDetector_Status_t *status;

    DoorDetector_init(NULL);
    DoorDetector_getConfig(&cfg);
    cfg.autoCalibrate = 0; /* Disable auto-calibration for deterministic test */
    DoorDetector_setConfig(&cfg);

    /* Point 0: Directly inside door zone (x=0.0, y=1.0, z=0.0) -> dist = 1.0m */
    pts[0].x = 0.0f; pts[0].y = 1.0f; pts[0].z = 0.0f; pts[0].velocity = 0.0f;
    info[0].snr = 200; /* 20.0 dB */

    /* Point 1: Outside lateral boundary (x=1.5m > 0.8m) */
    pts[1].x = 1.5f; pts[1].y = 1.0f; pts[1].z = 0.0f; pts[1].velocity = 0.0f;
    info[1].snr = 200;

    /* Point 2: Outside range (y=3.5m > 1.8m) */
    pts[2].x = 0.0f; pts[2].y = 3.5f; pts[2].z = 0.0f; pts[2].velocity = 0.0f;
    info[2].snr = 200;

    /* Point 3: Outside elevation (z=-1.8m < -1.0m) */
    pts[3].x = 0.0f; pts[3].y = 1.0f; pts[3].z = -1.8f; pts[3].velocity = 0.0f;
    info[3].snr = 200;

    DoorDetector_processFrame(pts, info, 4, 100);

    status = DoorDetector_getStatus();
    TEST_ASSERT(status->pointsInDoorZone == 1, "Only 1 point should fall inside the 3D ROI");
    TEST_ASSERT(fabsf(status->avgDoorDistance - 1.0f) < 0.01f, "Measured distance should be ~1.0m");

    TEST_PASS("3D Spatial Gating ROI Isolation");
}

/* -------------------------------------------------------------------------
 * Test 4: CFAR SNR Threshold Filtering
 * ------------------------------------------------------------------------- */
static void test_snr_threshold_filtering(void)
{
    DoorDetector_Config_t cfg;
    DoorPoint_t pt;
    DoorPointSideInfo_t info;
    const DoorDetector_Status_t *status;

    DoorDetector_init(NULL);
    DoorDetector_getConfig(&cfg);
    cfg.autoCalibrate = 0;
    cfg.minSnr = 15.0f; /* 15 dB threshold */
    DoorDetector_setConfig(&cfg);

    pt.x = 0.0f; pt.y = 1.0f; pt.z = 0.0f; pt.velocity = 0.0f;

    /* Sub-test A: Weak reflection (8.0 dB < 15.0 dB) -> Should be rejected */
    info.snr = 80; /* 8.0 dB */
    DoorDetector_processFrame(&pt, &info, 1, 100);

    status = DoorDetector_getStatus();
    TEST_ASSERT(status->pointsInDoorZone == 0, "Weak SNR reflection should be rejected");

    /* Sub-test B: Strong reflection (18.5 dB >= 15.0 dB) -> Should be accepted */
    info.snr = 185; /* 18.5 dB */
    DoorDetector_processFrame(&pt, &info, 1, 100);

    status = DoorDetector_getStatus();
    TEST_ASSERT(status->pointsInDoorZone == 1, "Strong SNR reflection should be accepted");
    TEST_ASSERT(fabsf(status->peakSnr - 18.5f) < 0.1f, "Peak SNR should be 18.5 dB");

    TEST_PASS("CFAR SNR Clutter Rejection");
}

/* -------------------------------------------------------------------------
 * Test 5: FSM Debouncing (CLOSED -> OPEN Transition)
 * ------------------------------------------------------------------------- */
static void test_fsm_closed_to_open_debounce(void)
{
    DoorDetector_Config_t cfg;
    DoorPoint_t pt;
    DoorPointSideInfo_t info;
    const DoorDetector_Status_t *status;
    int f;

    DoorDetector_init(NULL);
    DoorDetector_getConfig(&cfg);
    cfg.autoCalibrate = 0;
    cfg.debounceOpenFrames = 5;
    DoorDetector_setConfig(&cfg);

    pt.x = 0.0f; pt.y = 1.0f; pt.z = 0.0f; pt.velocity = 0.0f;
    info.snr = 200;

    /* Establish initial CLOSED state */
    DoorDetector_processFrame(&pt, &info, 1, 100);
    status = DoorDetector_getStatus();
    TEST_ASSERT(status->currentState == DOOR_STATE_CLOSED, "Should initialize to CLOSED");

    /* Now simulate door opening (0 points in zone) for 4 frames */
    for (f = 1; f <= 4; f++)
    {
        DoorDetector_processFrame(NULL, NULL, 0, 100);
        status = DoorDetector_getStatus();
        TEST_ASSERT(status->currentState == DOOR_STATE_CLOSED, "Must remain CLOSED during 1-4 debounce frames");
        TEST_ASSERT(status->openDebounceCounter == (uint16_t)f, "openDebounceCounter should increment");
    }

    /* On 5th consecutive frame, state MUST transition to OPEN */
    DoorDetector_processFrame(NULL, NULL, 0, 100);
    status = DoorDetector_getStatus();
    TEST_ASSERT(status->currentState == DOOR_STATE_OPEN, "Must transition to OPEN on 5th frame");
    TEST_ASSERT(status->totalOpenCount == 1, "totalOpenCount should be exactly 1");
    TEST_ASSERT(status->stateChangedFlag == 1, "stateChangedFlag should be set");

    TEST_PASS("Debounce Hysteresis: CLOSED -> OPEN Transition");
}

/* -------------------------------------------------------------------------
 * Test 6: Transient Noise Glitch Immunity
 * ------------------------------------------------------------------------- */
static void test_transient_noise_glitch_immunity(void)
{
    DoorDetector_Config_t cfg;
    DoorPoint_t pt;
    DoorPointSideInfo_t info;
    const DoorDetector_Status_t *status;

    DoorDetector_init(NULL);
    DoorDetector_getConfig(&cfg);
    cfg.autoCalibrate = 0;
    cfg.debounceOpenFrames = 5;
    DoorDetector_setConfig(&cfg);

    pt.x = 0.0f; pt.y = 1.0f; pt.z = 0.0f; pt.velocity = 0.0f;
    info.snr = 200;

    /* Initial CLOSED */
    DoorDetector_processFrame(&pt, &info, 1, 100);

    /* 3 frames of momentary RF dropout / obstruction */
    DoorDetector_processFrame(NULL, NULL, 0, 100);
    DoorDetector_processFrame(NULL, NULL, 0, 100);
    DoorDetector_processFrame(NULL, NULL, 0, 100);

    /* Door reflection returns before 5th frame */
    DoorDetector_processFrame(&pt, &info, 1, 100);

    status = DoorDetector_getStatus();
    TEST_ASSERT(status->currentState == DOOR_STATE_CLOSED, "State must remain CLOSED after transient glitch");
    TEST_ASSERT(status->openDebounceCounter == 0, "openDebounceCounter must reset back to 0");
    TEST_ASSERT(status->totalOpenCount == 0, "No false open counts should occur");

    TEST_PASS("Transient Noise Glitch Immunity");
}

/* -------------------------------------------------------------------------
 * Test 7: Auto-Calibration Baseline Convergence
 * ------------------------------------------------------------------------- */
static void test_auto_calibration_convergence(void)
{
    DoorDetector_Config_t cfg;
    DoorPoint_t pt;
    DoorPointSideInfo_t info;
    const DoorDetector_Status_t *status;
    int f;

    DoorDetector_init(NULL);
    DoorDetector_getConfig(&cfg);
    cfg.autoCalibrate = 1;
    cfg.calibFrameCount = 10;
    DoorDetector_setConfig(&cfg);

    /* Sensor placed 1.25m from closed door */
    pt.x = 0.0f; pt.y = 1.25f; pt.z = 0.0f; pt.velocity = 0.0f;
    info.snr = 220;

    for (f = 0; f < 10; f++)
    {
        DoorDetector_processFrame(&pt, &info, 1, 100);
    }

    status = DoorDetector_getStatus();
    TEST_ASSERT(status->isCalibrated == 1, "Sensor must be calibrated after 10 frames");
    TEST_ASSERT(status->currentState == DOOR_STATE_CLOSED, "Calibrated state must be CLOSED");

    DoorDetector_getConfig(&cfg);
    TEST_ASSERT(fabsf(cfg.rangeMin - (1.25f - 0.30f)) < 0.05f, "rangeMin should adapt around 1.25m");
    TEST_ASSERT(fabsf(cfg.rangeMax - (1.25f + 0.35f)) < 0.05f, "rangeMax should adapt around 1.25m");

    TEST_PASS("Auto-Calibration Baseline Convergence");
}

/* -------------------------------------------------------------------------
 * Test 8: VT100 Screen Formatting Safety & Buffer Bounds
 * ------------------------------------------------------------------------- */
static void test_vt100_screen_formatting_safety(void)
{
    char smallBuf[32];
    char largeBuf[2048];
    uint32_t written;

    DoorDetector_init(NULL);

    /* Test A: Buffer too small -> Should truncate safely without memory corruption */
    written = DoorDetector_formatVt100Screen(smallBuf, sizeof(smallBuf));
    TEST_ASSERT(written < sizeof(smallBuf), "Must not overflow small buffer");
    TEST_ASSERT(smallBuf[sizeof(smallBuf) - 1] == '\0', "Buffer must be null terminated");

    /* Test B: Adequate buffer -> Should write full VT100 dashboard */
    written = DoorDetector_formatVt100Screen(largeBuf, sizeof(largeBuf));
    TEST_ASSERT(written > 500, "Full VT100 dashboard should be > 500 bytes");
    TEST_ASSERT(strstr(largeBuf, "AWR1843BOOST") != NULL, "Header must contain AWR1843BOOST");
    TEST_ASSERT(strstr(largeBuf, "\x1B[H") != NULL, "Must contain cursor home escape code");

    TEST_PASS("VT100 Screen Formatting & Buffer Protection");
}

/* -------------------------------------------------------------------------
 * Test 9: Diagnostics and Thread-Safe Snapshot Retrieval
 * ------------------------------------------------------------------------- */
static void test_diagnostics_and_snapshots(void)
{
    DoorResult_e res;
    DoorDetector_Status_t snapshot;
    DoorDiagnostics_t diag;
    DoorPoint_t pt;
    DoorPointSideInfo_t info;

    DoorDetector_init(NULL);

    pt.x = 0.0f; pt.y = 1.0f; pt.z = 0.0f; pt.velocity = 0.0f;
    info.snr = 210;

    DoorDetector_processFrame(&pt, &info, 1, 100);

    /* Test snapshot copy */
    res = DoorDetector_getSnapshot(&snapshot);
    TEST_ASSERT(res == DOOR_OK, "getSnapshot should return DOOR_OK");
    TEST_ASSERT(snapshot.frameCount == 1, "Snapshot frame count should match");

    /* Test diagnostics */
    res = DoorDetector_getDiagnostics(&diag);
    TEST_ASSERT(res == DOOR_OK, "getDiagnostics should return DOOR_OK");
    TEST_ASSERT(diag.totalFramesProcessed == 1, "totalFramesProcessed should be 1");
    TEST_ASSERT(diag.totalPointsAnalyzed == 1, "totalPointsAnalyzed should be 1");
    TEST_ASSERT(diag.healthStatus == DOOR_HEALTH_OK, "healthStatus should be OK");

    TEST_PASS("Diagnostics and Thread-Safe Snapshot Retrieval");
}

/* -------------------------------------------------------------------------
 * Main Test Runner
 * ------------------------------------------------------------------------- */
int main(void)
{
    printf("\n========================================================\n");
    printf("  TI AWR1843BOOST Door Detector C Unit Test Suite\n");
    printf("========================================================\n\n");

    test_init_default_and_validation();
    test_invalid_parameters();
    test_spatial_gating_boundaries();
    test_snr_threshold_filtering();
    test_fsm_closed_to_open_debounce();
    test_transient_noise_glitch_immunity();
    test_auto_calibration_convergence();
    test_vt100_screen_formatting_safety();
    test_diagnostics_and_snapshots();

    printf("\n--------------------------------------------------------\n");
    printf("  Summary: %d Passed, %d Failed\n", s_testsPassed, s_testsFailed);
    printf("========================================================\n\n");

    return (s_testsFailed == 0) ? 0 : 1;
}
