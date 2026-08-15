Dear Editor-in-Chief,

I am pleased to submit our manuscript, "Does the Picture Matter? Image Representation as an
Unstudied Variable in Citation-Grounded Multimodal LLM Classification of IoT Network Traffic," for
consideration as an Original Paper in the *International Journal of Information Security*.

The manuscript asks whether a citation-grounding technique's effectiveness depends on how the
underlying network traffic is visually encoded, not just on the prompting strategy used. Holding
prompting condition, dataset, models, citation corpus, and grading rubric fixed, we compare six
image representations of the identical CIC-IoT-2023 traffic windows -- from a fully labeled,
legended composite chart to entirely unannotated numeric-to-pixel encodings, including one
genuinely 3-dimensional (height x width x 3-channel) RGB-stack encoding -- and measure both
classification accuracy and citation hallucination across two multimodal LLMs (Qwen-vl-plus and
GPT-4o-mini) at a real, completed $n=1{,}020$ confirmatory scale (6,120 API calls per model, zero
failed calls). We find a sharp, non-monotonic split: annotated representations sustain 42-80%
accuracy and 31-62% correct-citation rates, while unannotated representations collapse to
chance-level accuracy (~10%) for both models -- and this collapse is not a retreat into honest
uncertainty. Both models continue to volunteer confident citations even as their accuracy
collapses, and one model's failure mode is total: identical classification and citation output on
literally every one of 3,060 unannotated-image calls, regardless of the true underlying traffic.
This is evidence that stripping visual annotation causes hallucination through confident
fabrication, not honest hedging -- a distinction with direct practical consequences for anyone
deploying citation-grounded LLM classification, since a representation choice that looks purely
cosmetic can silently convert a pipeline's output from mostly correct to uniformly, confidently
wrong.

**Relationship to a companion submission.** This manuscript is a direct methodological extension
of a separate manuscript, "Grounding Reduces Citation Hallucination in Multimodal LLM Zero-Shot
Classification of IoT-Botnet Traffic -- A Two-Model Confirmatory Study," which we understand to be
under review at this journal. That study varied *prompting condition* while holding image
representation fixed; this study varies *image representation* while holding prompting condition
fixed at the earlier study's best-performing condition (RAG-grounded). The two manuscripts share a
dataset, a hand-verified citation corpus, and grading infrastructure, but report distinct
experimental designs, distinct independent variables, and distinct findings, and are intended to
be read as companion studies rather than overlapping or duplicate submissions. We disclose this
relationship for the editor's awareness and are happy to have both manuscripts reviewed together
or sequentially, whichever the journal prefers.

We believe this work is a good fit for the journal's scope at the intersection of applied machine
learning and network/IoT security, and that its findings -- particularly the sharp
annotated/unannotated threshold and the fabrication-not-hedging failure mode -- offer actionable
guidance for anyone designing a citation-grounded LLM security pipeline's visualization layer.

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
poonam.singh5@gmail.com
