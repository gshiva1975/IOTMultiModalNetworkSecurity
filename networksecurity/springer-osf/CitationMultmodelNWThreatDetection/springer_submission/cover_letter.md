Dear Editor-in-Chief,

I am pleased to submit our manuscript, "Grounding Reduces Citation Hallucination in Multimodal
LLM Zero-Shot Classification of IoT-Botnet Traffic -- A Two-Model Confirmatory Study," for
consideration as an Original Paper in the *International Journal of Information Security*.

The manuscript addresses a practical, timely problem in network security: large language models
increasingly used to triage IoT network traffic often justify their classifications with citations
to CVE/CAPEC identifiers, and these citations are prone to hallucination. We show that restricting
a model's citation menu to a small, independently verified reference corpus measurably improves
citation correctness, but that this same grounding technique's effect on raw classification
accuracy is model-dependent -- a finding established at matched confirmatory scale ($n=1{,}020$
per model) across two LLMs (Claude Sonnet and GPT-4o-mini) on byte-identical inputs, with
non-overlapping 95% confidence intervals between models in every prompting condition. We localize
a severe, previously unreported accuracy collapse in one model to a specific attack category
(Mirai botnet traffic) via direct inspection of misclassification patterns, and connect this
finding to the broader "contextual distraction" literature on retrieval-augmented generation. All
data, code, and the hand-verified reference corpus are released for reproducibility.

We believe this work is a good fit for the journal's scope at the intersection of applied machine
learning and network/IoT security, and that its methodology -- an externally verified,
single-source-of-truth citation corpus used both to constrain and to grade model output -- offers
a reusable evaluation instrument for future work on LLM-based security tooling.

This manuscript is original, has not been published previously, and is not under consideration by
any other journal. There are no conflicts of interest to declare. The corresponding author can be
reached at gshiva@sandiego.edu.

Thank you for considering our manuscript. We look forward to your response.

Sincerely,
Gangadhar Singh Shiva (corresponding author)
University of San Diego, San Diego, CA, USA
gshiva@sandiego.edu

Poonam Singh Umakanth
HPE Juniper Networking, Hewlett Packard Enterprise
