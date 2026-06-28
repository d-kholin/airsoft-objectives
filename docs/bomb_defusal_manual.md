# BOMB DEFUSAL MANUAL

**CLASSIFIED — FIELD OPERATIONS USE ONLY**

This manual is for the expert team communicating with the defuser over radio. The defuser can see the bomb but NOT this manual. The expert team has this manual but CANNOT see the bomb. Work together.

The bomb has a **serial number** (shown on screen, e.g. `AB1234`), a **countdown timer**, and several **modules**. All modules must be solved before the timer expires. Three strikes and the bomb detonates.

---

## MODULE 1: WIRES

The defuser will see 3–6 colored wires. They must describe the **number of wires** and **each wire's color in order** (top to bottom). Then use the rules below to determine which wire to cut.

### 3 Wires
- If there are no RED wires, cut the **2nd wire**.
- Otherwise, if the last wire is WHITE, cut the **last wire**.
- Otherwise, cut the **1st wire**.

### 4 Wires
- If there is more than one RED wire and the **last digit of the serial number is odd**, cut the **last RED wire**.
- Otherwise, if the last wire is YELLOW and there are no RED wires, cut the **1st wire**.
- Otherwise, if there is exactly one BLUE wire, cut the **1st wire**.
- Otherwise, cut the **2nd wire**.

### 5 Wires
- If the last wire is GREEN and the **last digit of the serial number is odd**, cut the **4th wire**.
- Otherwise, if there is exactly one RED wire and more than one YELLOW wire, cut the **1st wire**.
- Otherwise, if there are no GREEN wires, cut the **2nd wire**.
- Otherwise, cut the **1st wire**.

### 6 Wires
- If there are no YELLOW wires and the **last digit of the serial number is odd**, cut the **3rd wire**.
- Otherwise, if there is exactly one YELLOW wire and more than one WHITE wire, cut the **4th wire**.
- Otherwise, if there are no RED wires, cut the **last wire**.
- Otherwise, cut the **4th wire**.

---

## MODULE 2: KEYPAD

The defuser will see 4 symbols on the screen. They must read out all four symbol names. Find the **one column below** that contains all four of the defuser's symbols, then tell them to press the symbols in that column's **top-to-bottom order**.

| Column 1 | Column 2 | Column 3 | Column 4 | Column 5 | Column 6 |
|----------|----------|----------|----------|----------|----------|
| BOLT     | MOON     | GEAR     | STAR     | DART     | COIL     |
| STAR     | BOLT     | WAVE     | KNOT     | MOON     | GEAR     |
| DROP     | RING     | KNOT     | FANG     | COIL     | MOON     |
| GEAR     | WAVE     | DART     | RING     | APEX     | FANG     |
| KNOT     | STAR     | MOON     | GEAR     | DROP     | BOLT     |
| RING     | COIL     | DROP     | APEX     | FANG     | WAVE     |
| DART     | FANG     | APEX     | COIL     | BOLT     | KNOT     |

**Example:** If the defuser says "WAVE, DART, GEAR, KNOT", find Column 3 (which contains all four). The correct press order is: GEAR → WAVE → KNOT → DART.

---

## MODULE 3: THE BUTTON

The defuser will see a large colored button with a word on it. They must tell you the **button's color** and the **word on the button**.

### Step 1: Determine the action

Follow these rules **in order** — use the first rule that applies:

1. If the button is **BLUE** and the label says **"ABORT"** → **hold the button**.
2. If the label says **"DETONATE"** → **tap the button** (press and immediately release).
3. If the button is **WHITE** and the **serial number contains a vowel (A, E, I, O, U)** → **hold the button**.
4. If the button is **RED** and the label says **"HOLD"** → **tap the button**.
5. If none of the above apply → **hold the button**.

### Step 2: If holding the button

When the defuser holds the button (press GREEN and keep it held), a **colored strip** will appear. The defuser must tell you the strip's color, then release (press START) when the **countdown timer has a specific digit in the ones place**:

| Strip Color | Release when timer ones digit is: |
|-------------|----------------------------------|
| BLUE        | 4                                |
| YELLOW      | 5                                |
| Any other   | 1                                |

**Example:** If the strip is BLUE, the defuser should release when the timer shows any time ending in 4 (like 2:34, 1:14, 0:04, etc.).

---

## MODULE 4: CAPACITOR DISCHARGE

The defuser will see 3–4 capacitors, each with a **color** (RED, BLUE, GREEN, or YELLOW) and a **voltage** (1.5V–5.0V). They must tell you each capacitor's color and voltage, plus the **serial number** and which **indicators are lit** (shown at the top of the bomb screen). The capacitors must be discharged in a specific order — one wrong discharge is a strike.

### Step 1: Determine which rule set applies

Follow these rules **in order** — use the first that matches:

1. If **both FRK and CAR** indicators are lit → use **Rule Set A**
2. If **FRK** is lit (but not CAR) → use **Rule Set B**
3. If the **serial contains a vowel** AND the **last digit is odd** → use **Rule Set C**
4. Otherwise → use **Rule Set D**

### Step 2: Apply the rule set

**Rule Set A — Sort by color priority, then voltage:**

| Priority | Color  |
|----------|--------|
| 1st      | RED    |
| 2nd      | YELLOW |
| 3rd      | BLUE   |
| 4th      | GREEN  |

Discharge all REDs first (lowest voltage first within same color), then YELLOWs, etc.

**Rule Set B — Highest voltage first:**

Discharge from highest voltage to lowest. If tied, use color priority (RED > YELLOW > BLUE > GREEN).

**Rule Set C — Lowest voltage first, but RED caps last:**

Discharge all non-RED capacitors from lowest voltage to highest (color priority for ties), then discharge RED capacitors from lowest to highest.

**Rule Set D — Lowest voltage first:**

Discharge from lowest voltage to highest. If tied, use color priority (RED > YELLOW > BLUE > GREEN).

**Example:** Indicators FRK and CAR are both lit. Capacitors: GREEN 3.0V, RED 1.5V, BLUE 3.0V, YELLOW 4.5V. Rule Set A applies (both FRK and CAR lit). Sort by color priority: RED 1.5V → YELLOW 4.5V → BLUE 3.0V → GREEN 3.0V.

---

## MODULE 5: DETONATOR PINS

The defuser will see 4–5 numbered pins, each with a status: **ARMED**, **SAFE**, or **UNKNOWN**. They must tell you the **pin numbers and their statuses**, plus the **serial number**. The pins must be pulled in a specific order.

### Pull Order Rules

The order depends on the **last digit of the serial number** and whether the **serial contains a vowel (A, E, I, O, U)**:

### If the last digit of the serial is ODD:
1. Pull all **UNKNOWN** pins first (lowest number first)
2. Then all **ARMED** pins (highest number first)
3. Then all **SAFE** pins (lowest number first)

### If the last digit is EVEN and the serial CONTAINS a vowel:
1. Pull all **SAFE** pins first (lowest number first)
2. Then all **UNKNOWN** pins (highest number first)
3. Then all **ARMED** pins (lowest number first)

### If the last digit is EVEN and the serial DOES NOT contain a vowel:
1. Pull all **ARMED** pins first (lowest number first)
2. Then all **SAFE** pins (lowest number first)
3. Then all **UNKNOWN** pins (highest number first)

**Example:** Serial is AB1234 (last digit 4 = even, contains A = vowel). Pins: 1-ARMED, 2-SAFE, 3-UNKNOWN, 4-ARMED, 5-SAFE. Order: SAFE first (2, 5), then UNKNOWN (3), then ARMED (4, 1). → Pull order: 2, 5, 3, 4, 1.

---

## MODULE 6: NUMBER PAD

The defuser will see a **display showing a number (1–4)** and a set of **indicator lights** (labeled SIG, FRK, CAR, IND, MSA, BOB — some lit, some unlit). They must tell you: the **display number** and **which indicators are lit**.

Based on these, tell the defuser which number to select:

### Display shows 1:
- If **FRK** is lit and the **last digit of the serial is odd** → select **3**
- Otherwise, if **CAR** is lit → select **4**
- Otherwise → select **2**

### Display shows 2:
- If **SIG** and **FRK** are both lit → select **4**
- Otherwise, if the **last digit of the serial is odd** → select **1**
- Otherwise → select **3**

### Display shows 3:
- If **CAR** is lit and the **last digit of the serial is even** → select **1**
- Otherwise, if **SIG** is lit → select **2**
- Otherwise → select **4**

### Display shows 4:
- If **FRK** and **CAR** are both lit → select **2**
- Otherwise, if **SIG** is lit and the **last digit of the serial is odd** → select **3**
- Otherwise → select **1**

---

## GENERAL TIPS

- The defuser navigates between modules using RED (previous) and BLUE (next).
- Modules can be solved in any order.
- A wrong answer on any module counts as a **strike**. Three strikes = detonation.
- Stay calm, communicate clearly, and watch the timer.

---

*Good luck. Don't blow up.*
