# Catalyst — Front-end design (UI/UX and front-end engineering)

2026-10-18 · Mia

> **Superseded in part.** This document describes the first front end (sign-off page, a single proposal, the `/graph` + `/ops` API sketch, a Next.js template with a Streamlit fallback). What was built is a Vite + React + @xyflow/react single page on the API in `catalyst/api.py`, and plan B replaced sign-off with approving one plan per conclusion. The current front-end design is `docs/frontend/plan-b-design.md`, with `docs/frontend/` for the implementation plan and tests. The repository version is the source of truth.

> **Further change on 2026-10-19.** The Scenario Diff page (B3) described below was removed. Assumptions are now changed by editing a node in place on B1, and new causes are added on the canvas, so the product has two pages (B1 graph, B2 approve). Each question opens its own research workspace. See the 2026-10-19 revisions in `docs/engineering-design.md`.

## In one sentence, and the design principles

The front end is one view of a graph snapshot. It is not a second brain. The canvas only renders a version of the back end's ClaimGraph. Every action the user takes on the canvas is translated into one back-end operation (ChangeAssumption / AddShock / confirm / commit). The validator writes a new snapshot, and then the canvas redraws from it. The three pages map to the product's six stations: Research Workspace (check, conditions, evidence), Sign-off (sign), Scenario Diff (fork). Discover is the first screen of the Workspace.

Four principles. Every screen below can be traced back to them:

1.  **Few words, one number per screen.** Each page has only one big number and one main action (in the Workspace it is the condition's threshold, in the Diff it is the time limit for "what to check next"). Engineering information (version number, write scope, hash) stays off the main screen and goes in the detail layer. This is the conclusion of direction D (the Apple designer) on the design canvas.

2.  **Four layers of state are not merged into one badge.** What the scenario assumes, whether the evidence supports it, whether the condition can be verified and whether it is met, and whether the user has signed, are four separate things. Each has its own place and colour in the UI.

3.  **Never show a number that has no source.** After a fork, a node is only marked challenged / unaffected / unresolved. It does not show a propagated percentage such as "-15%". A number is shown only if it has a citation, and it carries the excerpt id.

4.  **The canvas is read-only, and actions are limited.** The user cannot edit node text or connect edges freely. What the user can do is change the value of one assumption, add a shock, confirm or change a threshold, and sign. This is how the engineering document's rule "the graph is written only through graph.commit" shows up on the front end.

## Information architecture

Three pages plus an input screen, with a fixed left navigation: Analyze / Sign-off / Scenarios / Evidence. Monitoring and Projects are greyed out in the three-hour version and the MVP (the slow loop is deferred).

| Page                     | The question it answers                         | Main elements                                                                                                                                                                                       | Station it maps to                    |
|--------------------------|-------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------|
| Input                    | What do you believe will happen?                | A one-line big-type belief, optional target chips (including "No target"), one button                                                                                                               | Station 1: event                      |
| Research Workspace (B1)  | How does it reach the instrument? What would prove me wrong? | With no target, first show up to 3 candidate cards (with the three kinds of label) or one line of abstention; click a card to enter the canvas + right panel (details / evidence / conditions); a fixed bottom toolbar "What if…" | Stations 2–4: discover, check, conditions |
| Sign-off (B2)            | Which ones do I sign?                           | A table of assumptions, one row each: assumption, invalidation condition, evidence status, user status; at the bottom the proposal card (WAIT / needs_review) and Sign                               | Station 6: proposal and sign-off      |
| Scenario Diff (B3)       | I changed one assumption. What changed?         | A toggle between baseline v1 and scenario v2; the canvas coloured by the three states; on the right "what to check next" + proposal v2                                                              | Station 5: fork                       |
| Evidence                 | What material did I cite?                       | The list of knowledge-base packs, the excerpts retrieved this round, each excerpt's stance and which edge cites it                                                                                  | The visible side of evidence before reasoning |

The reference drafts are three images (B1 / B2 / B3) that Mia made in another conversation (dark blue navigation, white cards, four-colour nodes). Take its layout, and change its content according to sections 3–5 of this document.

## Canvas specification

The canvas is a direct rendering of a ClaimGraph snapshot: node = Claim, edge = Mechanism, automatic layout (ELK, top to bottom). By default only 3 main stages are expanded (max_visible_hops), and the middle nodes are folded into one expandable group.

### Four kinds of node

| Node         | Comes from                          | Shown on the card                                                                           | Colour |
|--------------|-------------------------------------|---------------------------------------------------------------------------------------------|--------|
| Event        | The user's belief (root node)       | The user's own words + the one-line rewrite by the system (two lines; a tick once the user confirms) | blue   |
| Assumption   | A Claim in the middle of the chain  | One statement + small text for the evidence status (supported / contradicted / unknown) + the number of citations | green  |
| Outcome      | A terminal that resolves to a whitelisted instrument | The instrument and direction                                                  | purple |
| Risk / Shock | An external shock added by AddShock | One sentence + a dashed frame "assumed, not observed"                                       | orange |

There is only one key dependency. It is marked with a glowing outline + the small text "Check first". Nodes are not rated High / Medium / Low. An edge shows its one-line mechanism (expanded on hover). An edge with a citation is a solid line, and a model_only edge is dashed.

### State colouring (scenario page)

| State                      | Comes from          | Style                          |
|----------------------------|---------------------|--------------------------------|
| challenged                 | Scenario Assessment | orange border + orange dot     |
| unaffected                 | Scenario Assessment | grey fill + tick               |
| unresolved                 | Scenario Assessment | grey fill + dashed outline     |

These are a separate layer from the evidence status. A challenged node can still have the evidence status supported, and the card shows both.

### Mapping canvas actions to back-end operations

| What the user does on the canvas                                           | Operation it is translated into                  | Who decides                                                                        |
|----------------------------------------------------------------------------|--------------------------------------------------|------------------------------------------------------------------------------------|
| Click a node                                                               | Read-only: the right panel shows the details     | —                                                                                  |
| Change the value of an assumption on a node (such as the "opening date")   | ChangeAssumption (target, value)                 | The code computes the write scope, the model re-assesses inside the scope, the validator rejects anything out of bounds |
| Drag a Risk node in from the left column, or type "What if…" in the bottom toolbar | AddShock (statement); within three hours the attachment points are predefined | Same as above                                                      |
| Change a condition's threshold or deadline                                 | confirm_condition (threshold, deadline)          | The validator checks the type and the date; no model call                          |
| Click Confirm / Sign on the sign-off page                                  | confirm_claim / commit                           | Writes user_judgment, does not change the graph                                    |
| Edit node text, delete a node, connect edges freely                        | Not allowed (disabled in both the POC and the MVP) | —                                                                                |

After each successful operation the back end returns a new version number, and the front end redraws as a whole. The front end does not change node data in the local store. The "drag a node to change its position" that comes with the React Flow template is kept. Position is pure display state and does not go into the snapshot.

## Right panel

Click a node and the right panel has three tabs: details, evidence, conditions. The panel is where there are the most words in the whole front end, so it is collapsed by default and opens only when a node is clicked.

**Details**: the statement, the user's own words (if it was rewritten), the evidence status, the assessment under the current scenario, and the incoming and outgoing edges with their one-line mechanisms. A node that is the key dependency has one more line: "why check this step first".

**Evidence**: two stacks, Supporting (n) and Contradicting (n), taken from the stance of the evidence objects. Each evidence card shows: the source name, the date, the excerpt id (excerpt_id), a paragraph of the original text, and which sentence of this Claim it supports or contradicts. An edge with no evidence shows "model inference only", and no empty card is shown. The model's response to a contradicting excerpt (why it does not amount to a rebuttal) is shown under that card.

**Conditions** ("What would prove this wrong?"): each Condition takes one line of big text and one line of small text. The big text is plain language ("fewer than 20 a day by day 7"). The small text exposes the fields: observable or source · starting point (anchor) · deadline · threshold (if unknown, show "you decide", and it can be opened to fill in) · verifiable / not verified · met / not met / unknown. "Verifiable" and "met" are two badges, and are not merged. Changing a threshold or a deadline here is the only write action (confirm_condition).

The "Add" button in the reference draft is not built in the POC. Conditions are proposed by the model and the user edits the number. The user does not write them from scratch. This is a deliberate difference from products like Helm, where the user writes their own reasons.

## Sign-off page and fork page

### Sign-off (B2)

One table, one row per assumption, and a proposal card underneath. Columns: assumption, invalidation condition (plain language + deadline), evidence status, user status, action. The two status columns must be kept apart:

| Column          | Values                                  | Who writes it                    |
|-----------------|-----------------------------------------|----------------------------------|
| Evidence status | supported / contradicted / unknown      | The back end, advanced by citations |
| User status     | Not started / Needs review / Confirmed  | The user clicks Confirm          |

"Confirmed" means "I accept this assumption and its invalidation condition". It does not mean "the evidence holds". An assumption whose evidence is unknown can also be Confirmed, because what the user signs is the condition. The progress at the top, "3 / 6 confirmed", is kept.

Proposal card: the instrument and direction, the entry conditions (marked "and"), the invalidation conditions (marked "or"), the status. The status has only three words: WAIT, BLOCKED, Ready for review. There is no Ready to execute. Under the Sign button there is one line of small text: "What you sign is a research judgment, not an order". After signing, the proposal becomes a draft export, and the UI offers no execution button.

### Scenario Diff (B3)

At the top there is a toggle: baseline v1 / scenario v2. The scenario name is the sentence the user typed ("Iran is struck tomorrow"), with a small badge beside it: "assumed, not observed". The canvas is coloured by the three states (section 3), and the shock node has a dashed frame.

The right side is not a metrics table. It is three blocks:

1.  **Challenged premises**: which ones, and why (one sentence written by the model).

2.  **What to check next**: one event-type Condition. The big text is the time limit ("72 hours"), and the two branches are spelled out: if observed → keep waiting; if the window ends with nothing observed → the baseline continues.

3.  **Proposal v1 → v2**: whether the status changed, which condition changed, and which changed assumption it traces back to.

The "CoWoS -20%, GPU shipments -15%, Revenue -8% vs base case" in the reference draft is not built. That propagates a shock along the graph into percentages, and the engineering document has already removed probability and numeric propagation. A number with a citation (the material says "delayed by six months") can be shown on the shock node, with the excerpt id. "Save Scenario" = the snapshot is already stored, and the button only gives it a name.

## Front-end engineering

Choice: React Flow's [workflow editor template](https://reactflow.dev/ui/templates/workflow-editor) (Next.js + Tailwind + shadcn/ui + Zustand + ELKjs automatic layout). The editor is theirs, and the nodes and the panel are ours. The template page does not state a licence, and React Flow itself is MIT. Before using it, check the LICENSE in the ZIP.

| Reuse directly                                                 | Write ourselves                                                                 | Delete                                          |
|----------------------------------------------------------------|---------------------------------------------------------------------------------|-------------------------------------------------|
| Canvas, drag, zoom, minimap, keyboard operation                | 4 node components (Event / Assumption / Outcome / Risk, about 40–60 lines each) | Runner ("Run Workflow" runs nodes in order)     |
| Left drag bar (leave only Risk as draggable)                   | 1 edge component (mechanism text + solid / dashed line)                         | Transform / Join / Branch / Output nodes        |
| ELK automatic layout, dark mode, the Zustand store skeleton    | Right panel (details / evidence / conditions), the sign-off table, the three blocks of the Diff page | Node text editing, free edge connection, deleting nodes |
| shadcn Button / Badge / Table / Tabs / Sheet                   | API client (read snapshots, send operations)                                    | —                                               |

### Data contract

The back end gives the front end two interfaces. The front end does not keep its own truth about the graph:

- `GET /graph/{version}` → snapshot JSON: nodes (id, kind, statement, original_statement, evidence_status, is_key_dependency, assessment), edges (from, to, mechanism, evidence\[\] including stance / excerpt_id, model_only), conditions (claim_id, kind, predicate, observable, anchor, deadline, threshold nullable, verification_status, evaluation_status), proposal (direction, entry\[\], exit\[\], status, support_status), scenario (base_version, ops), retrieved_excerpts\[\].

- `POST /ops` → one operation (change_assumption / add_shock / confirm_condition / confirm_claim / commit), returning a new version number, or the validator's reason for rejecting it (the front end shows it as is).

The conversion from snapshot to React Flow is a pure function `toFlow(snapshot) → {nodes, edges}`: a node's data holds kind, state and whether it is the key dependency; an edge's data holds the mechanism and whether it is model_only. The Zustand store keeps only "the current version number + the selected node + the baseline version number being compared + node positions". Node content is recomputed from the snapshot each time and is not changed on the front end.

### Directory structure (suggested)

``` text
web/
  app/            pages: input / workspace / signoff / scenario / evidence
  components/
    nodes/        EventNode Assumption Node OutcomeNode RiskNode
    edges/        MechanismEdge
    panel/        Details Evidence Conditions
    signoff/      AssumptionTable ProposalCard
    scenario/     DiffSummary
  lib/
    api.ts        getGraph / postOp
    toFlow.ts     snapshot → nodes/edges
    status.ts     four layers of state → colour and wording (the only mapping table)
  store/          zustand: version, baseVersion, selectedNodeId, positions
```

The back end is still Python (engineering document), and the front end reads and writes through these two interfaces. In the POC the front end and back end are one process each, with no authentication.

## POC and MVP scope, time and fallback

|               | POC (35–90 minutes of the three hours)                                                                    | MVP                                                         |
|---------------|-----------------------------------------------------------------------------------------------------------|-------------------------------------------------------------|
| Input screen  | One input box + target chips                                                                              | Same, plus history                                          |
| Workspace     | Read-only canvas + right panel (details / evidence / conditions) + bottom What-if toolbar; candidate cards as the simplest list | Add dragging a Risk node from the left, folding / expanding middle nodes, the Evidence page |
| Sign-off      | One table + proposal card + Sign                                                                          | Add the history of each Confirm, export                     |
| Scenario Diff | Three-state colouring + three blocks on the right                                                         | Add baseline / scenario side by side, multiple scenarios    |
| Interaction   | change_assumption, add_shock (predefined attachment points), confirm_condition, commit                    | Add arbitrary shocks, confirm_claim                         |
| Time          | About 90 minutes with the React Flow template; saved from "ranking refinement" and "UI animation"         | —                                                           |

Fallback: if the front end is still not running by minute 115, switch to one Streamlit page: a Graphviz-rendered graph (coloured by the three states) + a condition list + the proposal card + one input box. There is no great loss of function. It just does not look good. This decision point goes into the schedule in the engineering document.

Source of the design drafts: direction D on the design canvas, the web version (the three screens input / argument / what-if), sets the word count and the mood. Mia's B1 / B2 / B3 reference images set the layout and navigation. If the two conflict, the four principles in section 1 of this document win.

## Open questions

- Do the candidate cards (Discover's 3 directions) go on the first screen of the Workspace, or on a separate page? The current decision is the first screen.

- When a folded middle node is expanded, should the highlight of the key dependency follow it into the folded group?

- Is "Needs review" in the Sign-off table pushed by the system (evidence contradicted or condition not verified) or marked by the user? The suggestion is the system.

- The template's licence is not confirmed.
