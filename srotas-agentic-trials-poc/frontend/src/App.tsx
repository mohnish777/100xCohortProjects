import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock3,
  Database,
  FileText,
  Mic,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  Workflow,
} from "lucide-react";

type CancerTrack = "breast" | "lung" | "prostate" | "mixed";
type MatchStatus = "eligible" | "possible_match" | "excluded";

type Patient = {
  id: string;
  display_name: string;
  anonymized_code: string;
  age_band: string;
  sex: string;
  cancer_track: CancerTrack;
};

type ClinicalFact = {
  key: string;
  display_name: string;
  description: string;
  value_type: "boolean" | "text" | "number" | "date";
  unit: string | null;
  oncology_track: CancerTrack;
  question_template: string;
  source: string;
};

type PatientFactValue = {
  patient_id: string;
  fact_key: string;
  value: boolean | string | number;
  display_value: string;
  evidence: string;
  confidence: number;
};

type Trial = {
  id: string;
  title: string;
  sponsor: string;
  cancer_track: CancerTrack;
  protocol_summary: string;
};

type TrialCriterion = {
  id: string;
  trial_id: string;
  criterion_type: "inclusion" | "exclusion";
  fact_key: string;
  operator: string;
  expected_value: boolean | string | number | null;
  display: string;
  source_quote: string;
  required: boolean;
};

type PatientMatch = {
  patient_id: string;
  patient_name: string;
  status: MatchStatus;
  explanation: string;
  missing_fact_keys: string[];
  matched_fact_keys: string[];
};

type FollowUpTask = {
  id: string;
  patient_id: string;
  patient_name: string;
  trial_id: string;
  fact_key: string;
  fact_display_name: string;
  question: string;
  status: "open" | "scheduled" | "completed" | "cancelled";
  priority: "low" | "medium" | "high";
  created_by_agent: string;
};

type AgentActivity = {
  agent_name: string;
  action: string;
  status: "done" | "active" | "queued";
};

type ProtocolLearningStep = {
  order: number;
  agent_name: string;
  title: string;
  detail: string;
};

type ProtocolLearningRun = {
  trial: Trial;
  source_filename: string | null;
  extraction_mode: "simulation" | "pdf_text";
  agent_mode: "deterministic" | "openai_structured";
  protocol_cache_status: "simulation" | "new_extraction" | "cached";
  protocol_hash: string | null;
  agent_notes: string[];
  protocol_excerpt: string;
  extracted_facts: ClinicalFact[];
  extracted_criteria: TrialCriterion[];
  matched_patients: PatientMatch[];
  follow_up_tasks: FollowUpTask[];
  steps: ProtocolLearningStep[];
};

type IntakeFactValue = {
  fact_key: string;
  display_name: string;
  value_type: "boolean" | "text" | "number" | "date";
  value: boolean | string | number | null;
  display_value: string;
  evidence: string;
  confidence: number;
};

type IntakeMissingFact = {
  fact_key: string;
  display_name: string;
  question: string;
  reason: string;
};

type IntakeAgentRun = {
  patient_id: string | null;
  agent_mode: "deterministic" | "openai_structured";
  transcript_excerpt: string;
  output: {
    patient_summary: string;
    inferred_cancer_track: CancerTrack;
    extracted_facts: IntakeFactValue[];
    missing_facts: IntakeMissingFact[];
    follow_up_questions: string[];
    trace_notes: string[];
    confidence: number;
  };
};

type DashboardSnapshot = {
  patients: Patient[];
  clinical_facts: ClinicalFact[];
  patient_fact_values: PatientFactValue[];
  selected_trial: Trial;
  trial_criteria: TrialCriterion[];
  matches: PatientMatch[];
  follow_up_tasks: FollowUpTask[];
  generated_sql: string;
  agent_activity: AgentActivity[];
};

type StorageStatus = {
  storage_mode: "memory_only" | "supabase_dual_write";
  supabase_url_configured: boolean;
  supabase_service_role_key_configured: boolean;
};

type BrowserSpeechRecognitionEvent = {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      isFinal: boolean;
      length: number;
      [index: number]: {
        transcript: string;
      };
    };
  };
};

type BrowserSpeechRecognitionErrorEvent = {
  error: string;
};

type BrowserSpeechRecognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onend: (() => void) | null;
  onerror: ((event: BrowserSpeechRecognitionErrorEvent) => void) | null;
  onresult: ((event: BrowserSpeechRecognitionEvent) => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const DEFAULT_INTAKE_TRANSCRIPT =
  "I have lung cancer. My report says NSCLC, and the cancer has spread. I had immunotherapy before, but I do not know my PD-L1 TPS.";
const INTAKE_AVATAR_QUESTIONS = [
  "What type of cancer were you diagnosed with?",
  "Do your reports mention a subtype, such as NSCLC, SCLC, HER2 status, or prostate cancer details?",
  "Has your cancer spread, or has it been called metastatic or stage four?",
  "Have you received chemotherapy, immunotherapy, hormonal therapy, or another cancer treatment before?",
  "Do you know any biomarker or lab results, such as PD-L1 TPS, EGFR, HER2, PSA, BRCA, or Gleason score?",
];

const fallbackSnapshot: DashboardSnapshot = {
  patients: [
    {
      id: "p_lung_014",
      display_name: "Patient L-014",
      anonymized_code: "LUNG-014",
      age_band: "50-59",
      sex: "female",
      cancer_track: "lung",
    },
    {
      id: "p_lung_027",
      display_name: "Patient L-027",
      anonymized_code: "LUNG-027",
      age_band: "60-69",
      sex: "male",
      cancer_track: "lung",
    },
    {
      id: "p_breast_009",
      display_name: "Patient B-009",
      anonymized_code: "BRST-009",
      age_band: "40-49",
      sex: "female",
      cancer_track: "breast",
    },
    {
      id: "p_prostate_021",
      display_name: "Patient P-021",
      anonymized_code: "PROS-021",
      age_band: "70-79",
      sex: "male",
      cancer_track: "prostate",
    },
  ],
  clinical_facts: [
    {
      key: "cancer_type",
      display_name: "Cancer type",
      description: "Primary oncology track reported by the patient.",
      value_type: "text",
      unit: null,
      oncology_track: "mixed",
      question_template: "What type of cancer were you diagnosed with?",
      source: "seed",
    },
    {
      key: "histology",
      display_name: "Histology",
      description: "Subtype such as NSCLC or SCLC.",
      value_type: "text",
      unit: null,
      oncology_track: "lung",
      question_template: "Do your reports mention NSCLC, SCLC, or another subtype?",
      source: "seed",
    },
    {
      key: "metastatic",
      display_name: "Metastatic disease",
      description: "Whether cancer is metastatic or advanced.",
      value_type: "boolean",
      unit: null,
      oncology_track: "mixed",
      question_template: "Has your cancer spread or been called metastatic?",
      source: "seed",
    },
    {
      key: "pd_l1_tps",
      display_name: "PD-L1 TPS",
      description: "PD-L1 tumor proportion score used for lung immunotherapy eligibility.",
      value_type: "number",
      unit: "%",
      oncology_track: "lung",
      question_template: "Do you have a PD-L1 TPS percentage on your pathology report?",
      source: "protocol_agent",
    },
  ],
  patient_fact_values: [
    {
      patient_id: "p_lung_014",
      fact_key: "cancer_type",
      value: "lung",
      display_value: "lung",
      evidence: "Patient described a lung cancer diagnosis.",
      confidence: 0.94,
    },
    {
      patient_id: "p_lung_014",
      fact_key: "histology",
      value: "NSCLC",
      display_value: "NSCLC",
      evidence: "Patient said the report mentions NSCLC.",
      confidence: 0.91,
    },
    {
      patient_id: "p_lung_014",
      fact_key: "metastatic",
      value: true,
      display_value: "true",
      evidence: "Patient said the cancer has spread.",
      confidence: 0.87,
    },
    {
      patient_id: "p_lung_027",
      fact_key: "pd_l1_tps",
      value: 72,
      display_value: "72%",
      evidence: "Pathology report lists PD-L1 TPS 72%.",
      confidence: 0.96,
    },
  ],
  selected_trial: {
    id: "trial_st_402",
    title: "ST-402 PD-L1 High NSCLC Study",
    sponsor: "Srotas Demo Network",
    cancer_track: "lung",
    protocol_summary: "Synthetic demo protocol requiring metastatic NSCLC and PD-L1 TPS >= 50.",
  },
  trial_criteria: [
    {
      id: "tc_001",
      trial_id: "trial_st_402",
      criterion_type: "inclusion",
      fact_key: "cancer_type",
      operator: "=",
      expected_value: "lung",
      display: "Cancer type equals lung",
      source_quote: "Participants must have lung cancer.",
      required: true,
    },
    {
      id: "tc_004",
      trial_id: "trial_st_402",
      criterion_type: "inclusion",
      fact_key: "pd_l1_tps",
      operator: ">=",
      expected_value: 50,
      display: "PD-L1 TPS is at least 50%",
      source_quote: "Participants must have PD-L1 TPS of at least 50%.",
      required: true,
    },
  ],
  matches: [
    {
      patient_id: "p_lung_014",
      patient_name: "Patient L-014",
      status: "possible_match",
      explanation: "Meets known lung, NSCLC, and metastatic criteria, but PD-L1 TPS is missing.",
      missing_fact_keys: ["pd_l1_tps"],
      matched_fact_keys: ["cancer_type", "histology", "metastatic"],
    },
    {
      patient_id: "p_lung_027",
      patient_name: "Patient L-027",
      status: "eligible",
      explanation: "Meets lung, NSCLC, metastatic, and PD-L1 TPS >= 50 criteria.",
      missing_fact_keys: [],
      matched_fact_keys: ["cancer_type", "histology", "metastatic", "pd_l1_tps"],
    },
  ],
  follow_up_tasks: [
    {
      id: "fu_001",
      patient_id: "p_lung_014",
      patient_name: "Patient L-014",
      trial_id: "trial_st_402",
      fact_key: "pd_l1_tps",
      fact_display_name: "PD-L1 TPS",
      question: "Can you confirm whether your pathology report shows a PD-L1 TPS percentage?",
      status: "open",
      priority: "high",
      created_by_agent: "fact_registry_agent",
    },
  ],
  generated_sql: `select p.id, p.anonymized_code
from patients p
join patient_fact_values cancer on cancer.patient_id = p.id
where cancer.fact_key = 'cancer_type'
  and cancer.value_text = 'lung';`,
  agent_activity: [
    {
      agent_name: "Intake Agent",
      action: "Stored lung cancer history as patient fact rows.",
      status: "done",
    },
    {
      agent_name: "Fact Registry Agent",
      action: "Registered pd_l1_tps without adding a patient table column.",
      status: "done",
    },
    {
      agent_name: "Voice Follow-up Agent",
      action: "Queued PD-L1 follow-up for Patient L-014.",
      status: "queued",
    },
  ],
};

const cancerTracks = [
  {
    name: "Breast",
    facts: "ER/PR, HER2, BRCA, stage, prior therapy",
  },
  {
    name: "Lung",
    facts: "NSCLC/SCLC, EGFR, ALK, PD-L1 TPS, immunotherapy",
  },
  {
    name: "Prostate",
    facts: "PSA, Gleason, ADT, docetaxel, castration resistance",
  },
];

const matchStyles: Record<MatchStatus, string> = {
  eligible: "border-emerald-200 bg-emerald-50 text-emerald-800",
  possible_match: "border-amber-200 bg-amber-50 text-amber-800",
  excluded: "border-slate-200 bg-slate-50 text-slate-600",
};

const agentStatusStyles: Record<AgentActivity["status"], string> = {
  done: "bg-emerald-100 text-emerald-800",
  active: "bg-coral/15 text-coral",
  queued: "bg-amber/15 text-amber",
};

function getSpeechRecognitionConstructor() {
  return window.SpeechRecognition ?? window.webkitSpeechRecognition;
}

function App() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot>(fallbackSnapshot);
  const [apiState, setApiState] = useState<"loading" | "live" | "fallback">("loading");
  const [storageStatus, setStorageStatus] = useState<StorageStatus | null>(null);
  const [protocolRun, setProtocolRun] = useState<ProtocolLearningRun | null>(null);
  const [protocolRunState, setProtocolRunState] = useState<"idle" | "running" | "done" | "error">(
    "idle",
  );
  const [protocolUploadError, setProtocolUploadError] = useState<string | null>(null);
  const [patientName, setPatientName] = useState("Aarav Sharma");
  const [intakeTranscript, setIntakeTranscript] = useState(DEFAULT_INTAKE_TRANSCRIPT);
  const [intakeRun, setIntakeRun] = useState<IntakeAgentRun | null>(null);
  const [intakeRunState, setIntakeRunState] = useState<"idle" | "running" | "done" | "error">(
    "idle",
  );
  const [intakeError, setIntakeError] = useState<string | null>(null);
  const [avatarQuestionIndex, setAvatarQuestionIndex] = useState(0);
  const [avatarMessage, setAvatarMessage] = useState(INTAKE_AVATAR_QUESTIONS[0]);
  const [voiceState, setVoiceState] = useState<"idle" | "listening" | "unsupported" | "error">(
    "idle",
  );
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [interimTranscript, setInterimTranscript] = useState("");
  const [incomingCallTask, setIncomingCallTask] = useState<FollowUpTask | null>(null);
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const transcriptBeforeVoiceRef = useRef("");
  const activeQuestionRef = useRef("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadSnapshot(signal?: AbortSignal) {
      try {
        const [response, storageResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/api/demo/clinical-memory`, {
            signal,
          }),
          fetch(`${API_BASE_URL}/api/demo/storage-status`, {
            signal,
          }),
        ]);

        if (!response.ok) {
          throw new Error(`API returned ${response.status}`);
        }

        const data = (await response.json()) as DashboardSnapshot;
        setSnapshot(data);
        if (storageResponse.ok) {
          setStorageStatus((await storageResponse.json()) as StorageStatus);
        }
        setApiState("live");
      } catch (error) {
        if (!signal?.aborted) {
          setSnapshot(fallbackSnapshot);
          setApiState("fallback");
        }
      }
    }

    loadSnapshot(controller.signal);

    return () => controller.abort();
  }, []);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
      window.speechSynthesis?.cancel();
    };
  }, []);

  const factByKey = useMemo(() => {
    return new Map(snapshot.clinical_facts.map((fact) => [fact.key, fact]));
  }, [snapshot.clinical_facts]);

  const activePatient = snapshot.patients[0];
  const activePatientFacts = snapshot.patient_fact_values.filter(
    (factValue) => factValue.patient_id === activePatient?.id,
  );

  const eligibleCount = snapshot.matches.filter((match) => match.status === "eligible").length;
  const possibleCount = snapshot.matches.filter(
    (match) => match.status === "possible_match",
  ).length;

  function syncProtocolRunWithSnapshot(nextSnapshot: DashboardSnapshot) {
    setProtocolRun((currentRun) => {
      if (!currentRun) {
        return currentRun;
      }

      return {
        ...currentRun,
        trial: nextSnapshot.selected_trial,
        extracted_criteria: nextSnapshot.trial_criteria,
        matched_patients: nextSnapshot.matches,
        follow_up_tasks: nextSnapshot.follow_up_tasks,
      };
    });
  }

  async function refreshSnapshot() {
    const [response, storageResponse] = await Promise.all([
      fetch(`${API_BASE_URL}/api/demo/clinical-memory`),
      fetch(`${API_BASE_URL}/api/demo/storage-status`),
    ]);

    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }

    const data = (await response.json()) as DashboardSnapshot;
    setSnapshot(data);
    if (storageResponse.ok) {
      setStorageStatus((await storageResponse.json()) as StorageStatus);
    }
    setApiState("live");
    return data;
  }

  async function runProtocolLearning() {
    setProtocolRunState("running");
    setProtocolUploadError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/demo/run-protocol-learning`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }

      const data = (await response.json()) as ProtocolLearningRun;
      setProtocolRun(data);
      setProtocolRunState("done");
      const nextSnapshot = await refreshSnapshot();
      syncProtocolRunWithSnapshot(nextSnapshot);
    } catch (error) {
      setProtocolRunState("error");
    }
  }

  async function resetDemoSession() {
    stopVoiceCapture();
    window.speechSynthesis?.cancel();
    setIntakeRun(null);
    setProtocolRun(null);
    setIntakeError(null);
    setProtocolUploadError(null);
    setIncomingCallTask(null);
    setAvatarQuestionIndex(0);
    setAvatarMessage(INTAKE_AVATAR_QUESTIONS[0]);
    setIntakeTranscript("");

    const response = await fetch(`${API_BASE_URL}/api/demo/reset-session`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        patient_name: patientName,
      }),
    });

    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }

    const data = (await response.json()) as DashboardSnapshot;
    setSnapshot(data);
    setApiState("live");
  }

  async function runIntakeAgent() {
    setIntakeRunState("running");
    setIntakeError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/demo/run-intake-agent`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          patient_id: activePatient?.id ?? "p_demo_001",
          patient_name: patientName,
          transcript: intakeTranscript,
        }),
      });

      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(body?.detail ?? `API returned ${response.status}`);
      }

      const data = (await response.json()) as IntakeAgentRun;
      setIntakeRun(data);
      setIntakeRunState("done");
      const nextSnapshot = await refreshSnapshot();
      syncProtocolRunWithSnapshot(nextSnapshot);
    } catch (error) {
      setIntakeRunState("error");
      setIntakeError(error instanceof Error ? error.message : "Intake extraction failed.");
    }
  }

  function stopVoiceCapture() {
    recognitionRef.current?.stop();
    setVoiceState("idle");
    setInterimTranscript("");
  }

  function startVoiceCapture(question = "") {
    const SpeechRecognition = getSpeechRecognitionConstructor();

    if (!SpeechRecognition) {
      setVoiceState("unsupported");
      setVoiceError(
        "Voice capture is not supported in this browser. Try Chrome or Safari, or type into the transcript box.",
      );
      return;
    }

    recognitionRef.current?.stop();
    activeQuestionRef.current = question;
    transcriptBeforeVoiceRef.current =
      intakeTranscript.trim() === DEFAULT_INTAKE_TRANSCRIPT ? "" : intakeTranscript.trim();

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognitionRef.current = recognition;

    recognition.onresult = (event) => {
      const finalParts: string[] = [];
      const interimParts: string[] = [];

      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const transcript = Array.from({ length: result.length }, (_, itemIndex) => {
          return result[itemIndex].transcript;
        }).join(" ");

        if (result.isFinal) {
          finalParts.push(transcript);
        } else {
          interimParts.push(transcript);
        }
      }

      if (interimParts.length > 0) {
        setInterimTranscript(interimParts.join(" ").trim());
      }

      if (finalParts.length > 0) {
        const answer = finalParts.join(" ").trim();
        const activeQuestion = activeQuestionRef.current;
        const baseTranscript = transcriptBeforeVoiceRef.current;
        const turn = activeQuestion
          ? `Avatar: ${activeQuestion}\nPatient: ${answer}`
          : answer;
        const nextTranscript = [baseTranscript, turn].filter(Boolean).join("\n\n");

        transcriptBeforeVoiceRef.current = nextTranscript;
        setIntakeTranscript(nextTranscript);
        setInterimTranscript("");
      }
    };

    recognition.onerror = (event) => {
      setVoiceState("error");
      setVoiceError(`Voice capture stopped: ${event.error}.`);
    };

    recognition.onend = () => {
      setVoiceState((currentState) => (currentState === "listening" ? "idle" : currentState));
    };

    try {
      recognition.start();
      setVoiceState("listening");
      setVoiceError(null);
    } catch (error) {
      setVoiceState("error");
      setVoiceError(error instanceof Error ? error.message : "Could not start voice capture.");
    }
  }

  function speakAvatarQuestion(question: string) {
    setAvatarMessage(question);

    if (!window.speechSynthesis) {
      startVoiceCapture(question);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(question);
    utterance.rate = 0.95;
    utterance.pitch = 1;
    utterance.onend = () => startVoiceCapture(question);
    utterance.onerror = () => startVoiceCapture(question);
    window.speechSynthesis.speak(utterance);
  }

  function askAvatarQuestion() {
    const question = INTAKE_AVATAR_QUESTIONS[avatarQuestionIndex];
    const nextIndex = (avatarQuestionIndex + 1) % INTAKE_AVATAR_QUESTIONS.length;

    setAvatarQuestionIndex(nextIndex);
    setVoiceError(null);
    speakAvatarQuestion(question);
  }

  function startFollowUpCall(task: FollowUpTask) {
    setIncomingCallTask(task);
    setAvatarMessage(`Incoming follow-up call for ${task.fact_display_name}`);
  }

  function answerFollowUpCall() {
    if (!incomingCallTask) {
      return;
    }

    const task = incomingCallTask;
    setIncomingCallTask(null);
    setVoiceError(null);
    speakAvatarQuestion(task.question);
  }

  async function uploadProtocol(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";

    if (!file) {
      return;
    }

    setProtocolRunState("running");
    setProtocolUploadError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE_URL}/api/demo/upload-protocol`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(body?.detail ?? `API returned ${response.status}`);
      }

      const data = (await response.json()) as ProtocolLearningRun;
      setProtocolRun(data);
      setProtocolRunState("done");
      const nextSnapshot = await refreshSnapshot();
      syncProtocolRunWithSnapshot(nextSnapshot);
    } catch (error) {
      setProtocolRunState("error");
      setProtocolUploadError(error instanceof Error ? error.message : "Protocol upload failed.");
    }
  }

  return (
    <main className="min-h-screen bg-[#f7faf9] text-ink">
      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-8 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-sage/20 bg-sage/10 px-3 py-1 text-sm font-medium text-sage">
              <Sparkles size={16} />
              Mixed-oncology adaptive trial agent
            </div>
            <h1 className="max-w-4xl text-4xl font-semibold tracking-normal text-ink md:text-5xl">
              Every new protocol teaches the system what patient facts matter.
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
              Patient intake and protocol upload now run through structured agents that extract
              reusable clinical facts, explain missing data, and prepare follow-up questions.
            </p>
          </div>

          <div className="grid min-w-64 grid-cols-3 gap-3 rounded border border-slate-200 bg-mist p-3">
            {cancerTracks.map((track) => (
              <div key={track.name} className="rounded bg-white p-3 shadow-sm">
                <div className="text-sm font-semibold">{track.name}</div>
                <div className="mt-1 text-xs leading-5 text-slate-500">{track.facts}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-4 px-6 pt-6 md:grid-cols-4">
        <MetricCard label="Patients" value={snapshot.patients.length.toString()} />
        <MetricCard label="Clinical facts" value={snapshot.clinical_facts.length.toString()} />
        <MetricCard label="Eligible" value={eligibleCount.toString()} />
        <MetricCard label="Need follow-up" value={possibleCount.toString()} />
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-6 py-6 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-lg font-semibold">Patient Voice Intake</h2>
              <p className="mt-1 text-sm text-slate-500">
                Demo patient history becomes rows in <code>patient_fact_values</code>.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={resetDemoSession}
                className="inline-flex h-10 items-center rounded border border-slate-300 px-4 text-sm font-semibold text-slate-700"
              >
                Clear demo data
              </button>
              <button
                onClick={voiceState === "listening" ? stopVoiceCapture : askAvatarQuestion}
                className="inline-flex h-10 items-center gap-2 rounded bg-sage px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Mic size={18} />
                {voiceState === "listening" ? "Stop listening" : "Ask question"}
              </button>
            </div>
          </div>

          <div className="mt-5 grid gap-5 md:grid-cols-[220px_1fr]">
            <div className="flex aspect-square flex-col items-center justify-center rounded bg-gradient-to-br from-sage to-coral p-4 text-center text-white">
              <div className="flex h-28 w-28 items-center justify-center rounded-full border border-white/40 bg-white/10">
                <Activity size={52} />
              </div>
              <div className="mt-4 text-xs font-semibold uppercase tracking-wide text-white/70">
                Intake avatar
              </div>
              <p className="mt-2 text-sm leading-5">{avatarMessage}</p>
              {voiceState === "listening" ? (
                <div className="mt-3 rounded-full border border-white/40 px-3 py-1 text-xs font-semibold">
                  Listening
                </div>
              ) : null}
            </div>
            <div className="space-y-3">
              <div className="rounded border border-slate-200 bg-white p-4">
                <label
                  className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                  htmlFor="patient-name"
                >
                  Patient name
                </label>
                <input
                  id="patient-name"
                  value={patientName}
                  onChange={(event) => setPatientName(event.target.value)}
                  className="mt-2 h-10 w-full rounded border border-slate-200 px-3 text-sm font-semibold text-slate-700 outline-none focus:border-sage"
                />
                <div className="mt-2 text-xs leading-5 text-slate-500">
                  Dashboard display name: {activePatient?.display_name ?? patientName}
                </div>
              </div>
              <div className="rounded border border-slate-200 bg-slate-50 p-4">
                <label
                  className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                  htmlFor="intake-transcript"
                >
                  Intake transcript
                </label>
                <textarea
                  id="intake-transcript"
                  value={intakeTranscript}
                  onChange={(event) => setIntakeTranscript(event.target.value)}
                  className="mt-2 min-h-32 w-full resize-y rounded border border-slate-200 bg-white p-3 text-sm leading-6 text-slate-700 outline-none focus:border-sage"
                />
                {interimTranscript ? (
                  <div className="mt-2 rounded border border-sage/20 bg-sage/5 px-3 py-2 text-sm leading-6 text-slate-600">
                    Hearing: {interimTranscript}
                  </div>
                ) : null}
                {voiceError ? (
                  <div className="mt-2 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm leading-6 text-amber-900">
                    {voiceError}
                  </div>
                ) : null}
                {incomingCallTask ? (
                  <div className="mt-3 rounded border border-coral/30 bg-coral/10 p-3">
                    <div className="text-xs font-semibold uppercase tracking-wide text-coral">
                      Incoming follow-up call
                    </div>
                    <div className="mt-1 text-sm font-semibold text-ink">
                      {incomingCallTask.patient_name}
                    </div>
                    <p className="mt-1 text-sm leading-6 text-slate-700">
                      {incomingCallTask.question}
                    </p>
                    <button
                      onClick={answerFollowUpCall}
                      className="mt-3 inline-flex h-9 items-center gap-2 rounded bg-coral px-3 text-sm font-semibold text-white"
                    >
                      <Mic size={16} />
                      Answer call
                    </button>
                  </div>
                ) : null}
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    onClick={voiceState === "listening" ? stopVoiceCapture : askAvatarQuestion}
                    className="inline-flex h-9 items-center gap-2 rounded border border-sage px-3 text-sm font-semibold text-sage"
                  >
                    <Mic size={16} />
                    {voiceState === "listening" ? "Stop mic" : "Ask next question"}
                  </button>
                  <button
                    onClick={runIntakeAgent}
                    disabled={intakeRunState === "running"}
                    className="inline-flex h-9 items-center gap-2 rounded bg-sage px-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <Sparkles size={16} />
                    {intakeRunState === "running" ? "Extracting facts" : "Extract facts"}
                  </button>
                  <button
                    onClick={() => {
                      stopVoiceCapture();
                      setIntakeTranscript(DEFAULT_INTAKE_TRANSCRIPT);
                      setAvatarQuestionIndex(0);
                      setAvatarMessage(INTAKE_AVATAR_QUESTIONS[0]);
                      setVoiceError(null);
                    }}
                    className="inline-flex h-9 items-center rounded border border-slate-300 px-3 text-sm font-semibold text-slate-700"
                  >
                    Reset sample
                  </button>
                </div>
              </div>

              {intakeRun ? (
                <div className="rounded border border-sage/30 bg-sage/5 p-4">
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-sage">
                      {intakeRun.agent_mode === "openai_structured"
                        ? "OpenAI structured Intake Agent"
                        : "Deterministic fallback intake"}
                    </span>
                    <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-500">
                      {intakeRun.output.inferred_cancer_track}
                    </span>
                    <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-500">
                      {Math.round(intakeRun.output.confidence * 100)}% confidence
                    </span>
                  </div>
                  <p className="text-sm leading-6 text-slate-700">
                    {intakeRun.output.patient_summary}
                  </p>
                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    {intakeRun.output.extracted_facts.map((fact) => (
                      <div key={fact.fact_key} className="rounded border border-sage/20 bg-white p-3">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="text-xs text-slate-500">{fact.display_name}</div>
                            <div className="mt-1 text-sm font-semibold">{fact.display_value}</div>
                          </div>
                          <code>{fact.fact_key}</code>
                        </div>
                        <p className="mt-2 text-xs leading-5 text-slate-500">{fact.evidence}</p>
                      </div>
                    ))}
                  </div>
                  {intakeRun.output.missing_facts.length > 0 ? (
                    <div className="mt-4 rounded border border-amber-200 bg-amber-50 p-3">
                      <div className="text-xs font-semibold uppercase text-amber-900">
                        Missing data closure
                      </div>
                      <div className="mt-2 space-y-2">
                        {intakeRun.output.missing_facts.map((missing) => (
                          <div key={missing.fact_key} className="text-sm leading-6 text-amber-950">
                            <span className="font-semibold">{missing.display_name}: </span>
                            {missing.question}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  {intakeRun.output.trace_notes.length > 0 ? (
                    <div className="mt-3 text-xs leading-5 text-slate-500">
                      {intakeRun.output.trace_notes.join(" ")}
                    </div>
                  ) : null}
                </div>
              ) : intakeRunState === "error" ? (
                <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
                  {intakeError ??
                    "Intake extraction failed. Check that the FastAPI backend is running on port 8000."}
                </div>
              ) : null}

              <div className="rounded border border-slate-200 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold">
                      {activePatient?.display_name ?? patientName}
                    </div>
                    <div className="text-xs text-slate-500">
                      Active demo patient, {activePatient?.age_band ?? "Not captured"},{" "}
                      {activePatient?.cancer_track ?? "mixed"}
                    </div>
                  </div>
                  <span className="rounded-full bg-amber/15 px-3 py-1 text-xs font-semibold text-amber">
                    {snapshot.follow_up_tasks.length > 0
                      ? `Missing ${snapshot.follow_up_tasks[0].fact_display_name}`
                      : "Ready for matching"}
                  </span>
                </div>
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {activePatientFacts.length > 0 ? (
                    activePatientFacts.map((factValue) => {
                    const fact = factByKey.get(factValue.fact_key);

                    return (
                      <div
                        key={`${factValue.patient_id}-${factValue.fact_key}`}
                        className="rounded border border-slate-200 bg-mist px-3 py-2"
                      >
                        <div className="text-xs text-slate-500">
                          {fact?.display_name ?? factValue.fact_key}
                        </div>
                        <div className="mt-1 text-sm font-semibold">{factValue.display_value}</div>
                      </div>
                    );
                    })
                  ) : (
                    <div className="rounded border border-dashed border-slate-300 bg-mist px-3 py-4 text-sm text-slate-500 sm:col-span-2">
                      No patient facts stored yet. Ask the avatar questions, answer them, then
                      extract facts.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-lg font-semibold">Coordinator Cockpit</h2>
              <p className="mt-1 text-sm text-slate-500">
                Protocol-derived facts drive matching and missing-data closure.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <label className="inline-flex h-10 cursor-pointer items-center gap-2 rounded border border-slate-300 px-4 text-sm font-semibold text-slate-700">
                <Upload size={18} />
                Upload PDF
                <input
                  className="sr-only"
                  type="file"
                  accept="application/pdf"
                  onChange={uploadProtocol}
                  disabled={protocolRunState === "running"}
                />
              </label>
              <button
                onClick={runProtocolLearning}
                disabled={protocolRunState === "running"}
                className="inline-flex h-10 items-center gap-2 rounded border border-slate-300 px-4 text-sm font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Search size={18} />
                {protocolRunState === "running" ? "Extracting" : "Run demo"}
              </button>
            </div>
          </div>

          <div className="mt-5 space-y-4">
            <div className="rounded border border-slate-200 p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                <FileText size={18} className="text-sage" />
                {snapshot.selected_trial.title}
              </div>
              <p className="text-sm leading-6 text-slate-600">
                {snapshot.selected_trial.protocol_summary}
              </p>
            </div>
            <div className="rounded border border-slate-200 p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                <Database size={18} className="text-sage" />
                Extracted inclusion criteria
              </div>
              <div className="space-y-2">
                {snapshot.trial_criteria.map((criterion) => (
                  <div
                    key={criterion.id}
                    className="flex items-start justify-between gap-3 rounded bg-slate-50 px-3 py-2"
                  >
                    <div>
                      <div className="text-sm font-medium">{criterion.display}</div>
                      <div className="mt-1 text-xs text-slate-500">{criterion.source_quote}</div>
                    </div>
                    <code className="shrink-0">{criterion.fact_key}</code>
                  </div>
                ))}
              </div>
            </div>

            {protocolRun ? (
              <div className="rounded border border-sage/30 bg-sage/5 p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-sage">
                  <Sparkles size={18} />
                  Protocol learning result
                </div>
                <div className="mb-3 flex flex-wrap gap-2 text-xs font-semibold text-slate-500">
                  <span className="rounded-full bg-white px-3 py-1">
                    {protocolRun.extraction_mode === "pdf_text"
                      ? "PDF text extraction"
                      : "Simulated protocol"}
                  </span>
                  <span className="rounded-full bg-white px-3 py-1">
                    {protocolRun.agent_mode === "openai_structured"
                      ? "OpenAI structured Protocol Agent"
                      : "Deterministic fallback agent"}
                  </span>
                  {protocolRun.source_filename ? (
                    <span className="rounded-full bg-white px-3 py-1">
                      {protocolRun.source_filename}
                    </span>
                  ) : null}
                  <span
                    className={`rounded-full px-3 py-1 ${
                      protocolRun.protocol_cache_status === "cached"
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-white"
                    }`}
                  >
                    {protocolRun.protocol_cache_status === "cached"
                      ? "Reused stored criteria"
                      : protocolRun.protocol_cache_status === "new_extraction"
                        ? "New extraction stored"
                        : "Demo criteria"}
                  </span>
                  {protocolRun.protocol_hash ? (
                    <span className="rounded-full bg-white px-3 py-1">
                      Hash {protocolRun.protocol_hash.slice(0, 8)}
                    </span>
                  ) : null}
                </div>
                <p className="text-sm leading-6 text-slate-700">{protocolRun.protocol_excerpt}</p>
                {protocolRun.agent_notes.length > 0 ? (
                  <div className="mt-3 rounded border border-sage/20 bg-white p-3">
                    <div className="text-xs font-semibold uppercase text-slate-500">
                      Agent trace notes
                    </div>
                    <ul className="mt-2 space-y-1 text-sm leading-6 text-slate-600">
                      {protocolRun.agent_notes.map((note) => (
                        <li key={note}>{note}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  {protocolRun.extracted_facts.map((fact) => (
                    <div key={fact.key} className="rounded border border-sage/20 bg-white p-3">
                      <div className="text-xs font-semibold uppercase text-slate-500">
                        {fact.value_type}
                      </div>
                      <div className="mt-1 text-sm font-semibold">{fact.display_name}</div>
                      <code className="mt-2 inline-block">{fact.key}</code>
                    </div>
                  ))}
                </div>
              </div>
            ) : protocolRunState === "error" ? (
              <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
                {protocolUploadError ??
                  "Protocol run failed. Check that the FastAPI backend is running on port 8000."}
              </div>
            ) : null}
          </div>
        </div>
      </section>

      {protocolRun ? (
        <section className="mx-auto max-w-7xl px-6 pb-6">
          <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">How The Protocol Taught The System</h2>
            <div className="mt-4 grid gap-3 md:grid-cols-4">
              {protocolRun.steps.map((step) => (
                <div key={step.order} className="rounded border border-slate-200 p-4">
                  <div className="mb-3 flex h-8 w-8 items-center justify-center rounded bg-sage/10 text-sm font-bold text-sage">
                    {step.order}
                  </div>
                  <div className="text-sm font-semibold">{step.title}</div>
                  <div className="mt-1 text-xs font-medium text-coral">{step.agent_name}</div>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{step.detail}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      <section className="mx-auto grid max-w-7xl gap-6 px-6 pb-6 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-2 text-lg font-semibold">
            <Workflow size={20} className="text-coral" />
            Match Results
          </div>
          <div className="space-y-3">
            {snapshot.matches.length > 0 ? (
              snapshot.matches.map((match) => (
              <div key={match.patient_id} className="rounded border border-slate-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold">{match.patient_name}</div>
                    <div className="mt-1 text-sm text-slate-500">{match.explanation}</div>
                  </div>
                  <span
                    className={`rounded-full border px-3 py-1 text-xs font-semibold ${matchStyles[match.status]}`}
                  >
                    {formatStatus(match.status)}
                  </span>
                </div>
                {match.missing_fact_keys.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {match.missing_fact_keys.map((factKey) => (
                      <span
                        key={factKey}
                        className="inline-flex items-center gap-1 rounded bg-amber/15 px-2 py-1 text-xs font-semibold text-amber"
                      >
                        <AlertCircle size={13} />
                        Missing {factByKey.get(factKey)?.display_name ?? factKey}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
              ))
            ) : (
              <div className="rounded border border-dashed border-slate-300 p-4 text-sm leading-6 text-slate-500">
                No match run yet. Capture patient details and upload a protocol to run matching.
              </div>
            )}
          </div>
        </div>

        <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-2 text-lg font-semibold">
            <ShieldCheck size={20} className="text-coral" />
            Safe SQL Preview
          </div>
          <pre className="max-h-[360px] overflow-auto rounded bg-ink p-4 text-xs leading-6 text-white">
            {snapshot.generated_sql}
          </pre>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            This is preview-only in the POC. Later the backend will validate and execute read-only
            queries against Supabase.
          </p>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-6 pb-8 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold">Follow-up Queue</h2>
          <div className="mt-4 space-y-3">
            {snapshot.follow_up_tasks.length > 0 ? (
              snapshot.follow_up_tasks.map((task) => (
              <div
                key={task.id}
                className="rounded border border-amber-200 bg-amber-50 p-4 text-amber-900"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="font-semibold">{task.patient_name}</div>
                  <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase">
                    {task.priority}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-6">{task.question}</p>
                <div className="mt-3 text-xs font-semibold">
                  Stores answer back as <code>{task.fact_key}</code> in patient_fact_values
                </div>
                <button
                  onClick={() => startFollowUpCall(task)}
                  className="mt-3 inline-flex h-9 items-center gap-2 rounded bg-amber px-3 text-sm font-semibold text-white"
                >
                  <Mic size={16} />
                  Call patient
                </button>
              </div>
              ))
            ) : (
              <div className="rounded border border-dashed border-slate-300 p-4 text-sm leading-6 text-slate-500">
                No follow-up tasks yet. Missing protocol-required facts will appear here.
              </div>
            )}
          </div>
        </div>

        <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Agent Activity Timeline</h2>
            <div className="flex flex-wrap justify-end gap-2">
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold ${
                  apiState === "live"
                    ? "bg-emerald-100 text-emerald-800"
                    : apiState === "loading"
                      ? "bg-slate-100 text-slate-600"
                      : "bg-amber/15 text-amber"
                }`}
              >
                {apiState === "live" ? "Backend live" : apiState === "loading" ? "Loading" : "Fallback data"}
              </span>
              {storageStatus ? (
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    storageStatus.storage_mode === "supabase_dual_write"
                      ? "bg-sage/15 text-sage"
                      : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {storageStatus.storage_mode === "supabase_dual_write"
                    ? "Supabase dual-write"
                    : "Memory storage"}
                </span>
              ) : null}
            </div>
          </div>
          <div className="mt-4 space-y-3">
            {snapshot.agent_activity.map((step, index) => (
              <div key={`${step.agent_name}-${index}`} className="rounded border border-slate-200 p-3">
                <div className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-mist text-sm font-bold">
                    {step.status === "done" ? <CheckCircle2 size={17} /> : <Clock3 size={17} />}
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="text-sm font-semibold">{step.agent_name}</div>
                      <span className={`rounded-full px-2 py-0.5 text-xs ${agentStatusStyles[step.status]}`}>
                        {step.status}
                      </span>
                    </div>
                    <div className="mt-1 text-sm leading-6 text-slate-600">{step.action}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </div>
  );
}

function formatStatus(status: MatchStatus) {
  return status.replace("_", " ");
}

export default App;
