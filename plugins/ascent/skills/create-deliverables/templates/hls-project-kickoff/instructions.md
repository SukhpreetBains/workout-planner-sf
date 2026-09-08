# HLS kickoff custom instructions

When this template is selected, build its labeled template preview and show
`template-choices.html` before asking content questions. Display all three
background images together, labeled A (Cyan molecules), B (Open horizon), and
C (Winding road). Do not substitute text-only options for the images.

Ask which image the user would like behind the top of the microsite. Save the
selected value (`molecules`, `horizon`, or `winding-road`) in the intake answer
`hls-project-kickoff.cover-background`, with `status: answered`,
`answered_by: user`, and `disposition: rendered`. Never infer this preference
from reviewed tracker content or copy the fictional example answer.

On resume, retain the explicit choice and do not ask again unless the user wants
to change it or the answer is conflicting. Ask for a replacement if the saved
value is no longer available. If the user requests a draft before choosing,
keep the question missing or deferred and use the solid cover. Normal required
gap and final-override rules still apply. A user may choose no photo by explicitly
marking the question not applicable with a reason.

Use all three approved illustrations in the selected sections: healthcare with
purpose and scope, the whiteboard with working agreements, and the high-five
with next steps. If a user omits one of those modules, omit its illustration too.
Keep these decorative accents separate from factual project content.
