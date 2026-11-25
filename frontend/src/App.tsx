import React, { Component, ErrorInfo, ReactNode, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Brain,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Clock,
  Database,
  Edit3,
  FileText,
  Filter,
  Flag,
  HeartPulse,
  Lock,
  LogOut,
  Menu,
  Microscope,
  Moon,
  Pill,
  Plus,
  Presentation,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Sun,
  Trash2,
  UserPlus,
  Users,
  X,
} from 'lucide-react';
import {
  AIQueryResponse,
  AISummaryResponse,
  CitationRef,
  DashboardData,
  Medication,
  PatientDetail,
  PatientListItem,
  SummaryStatement,
  User,
  Visit,
} from './api';
import {
  AlertBanner,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Modal,
  Select,
  SkeletonBlock,
  Textarea,
} from './components/ui';

const PRESET_QUESTIONS = [
  "What were this patient's previous diagnoses?",
  "Has this patient reported similar symptoms before?",
  "What medications were prescribed during previous visits?",
  "Show the patient's medical history from the last two years.",
  "Find previous records mentioning recurring headaches.",
  "Summarise all previous consultations related to diabetes or neuropathy.",
];

const BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
const PAGE_SIZE = 6;

class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean; message: string }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, message: error.message || 'Unexpected rendering failure.' };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('UI ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-canvas flex items-center justify-center p-6">
          <Card className="max-w-md w-full p-6 space-y-4 border-[#DC2011]">
            <div className="flex items-center gap-2.5 text-[#DC2011] font-semibold text-base">
              <AlertTriangle className="w-5 h-5" />
              <span>Clinical Workspace Recovery</span>
            </div>
            <p className="text-sm text-ink-secondary leading-relaxed">
              The interface encountered an unexpected error: {this.state.message}
            </p>
            <Button variant="primary" onClick={() => window.location.reload()}>
              Reload Workspace
            </Button>
          </Card>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  return (
    <ErrorBoundary>
      <MedVaultWorkspace />
    </ErrorBoundary>
  );
}

function readStoredUser(): User | null {
  try {
    const raw = sessionStorage.getItem('medvault_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function MedVaultWorkspace() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('medvault_theme');
    return saved === 'dark' ? 'dark' : 'light';
  });

  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem('medvault_token'));
  const [currentUser, setCurrentUser] = useState<User | null>(readStoredUser);

  // Login State
  const [email, setEmail] = useState('dr.sharma@medvault.edu');
  const [password, setPassword] = useState('Doctor@123');
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(false);

  // Navigation & Feedback State
  const [activeNav, setActiveNav] = useState<'dashboard' | 'patients' | 'patient_detail' | 'ai_retrieval' | 'audit'>('dashboard');
  const [patientSubTab, setPatientSubTab] = useState<'timeline' | 'ai_summary' | 'ai_ask' | 'new_visit'>('timeline');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Data State
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [patients, setPatients] = useState<PatientListItem[]>([]);
  const [patientsLoading, setPatientsLoading] = useState(false);
  const [patientSearch, setPatientSearch] = useState('');
  const [sexFilter, setSexFilter] = useState('');
  const [bloodGroupFilter, setBloodGroupFilter] = useState('');
  const [sortBy, setSortBy] = useState<'updated' | 'name' | 'visits' | 'mrn'>('updated');
  const [currentPage, setCurrentPage] = useState(1);

  const [selectedPatient, setSelectedPatient] = useState<PatientDetail | null>(null);
  const [visitTypeFilter, setVisitTypeFilter] = useState('');
  const [visitSearch, setVisitSearch] = useState('');

  const [aiSummary, setAiSummary] = useState<AISummaryResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [flaggedClaims, setFlaggedClaims] = useState<Record<string, boolean>>({});
  const [medCatalog, setMedCatalog] = useState<Medication[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [auditFilter, setAuditFilter] = useState('');

  // Citation Inspector Drawer State
  const [inspectedCitation, setInspectedCitation] = useState<CitationRef | null>(null);
  const [highlightedVisitId, setHighlightedVisitId] = useState<number | null>(null);

  // AI Retrieval State
  const [nlQuery, setNlQuery] = useState('Find previous records mentioning recurring headaches.');
  const [queryPatientScope, setQueryPatientScope] = useState<number | 'all'>('all');
  const [nlResult, setNlResult] = useState<AIQueryResponse | null>(null);
  const [nlLoading, setNlLoading] = useState(false);

  const searchInputRef = useRef<HTMLInputElement>(null);

  // Modals State
  const [showNewPatientModal, setShowNewPatientModal] = useState(false);
  const [submittingPatient, setSubmittingPatient] = useState(false);
  const [newPat, setNewPat] = useState({
    first_name: '',
    last_name: '',
    date_of_birth: '1990-05-15',
    sex: 'Male',
    blood_group: 'O+',
    phone: '+91-98111-00000',
    email: '',
    address: '',
    emergency_contact_name: '',
    emergency_contact_phone: '',
    allergy_allergen: '',
    allergy_reaction: '',
    history_condition: '',
  });

  const [showEditPatientModal, setShowEditPatientModal] = useState(false);
  const [editPat, setEditPat] = useState({
    first_name: '',
    last_name: '',
    date_of_birth: '',
    sex: 'Male',
    blood_group: '',
    phone: '',
    email: '',
    address: '',
    emergency_contact_name: '',
    emergency_contact_phone: '',
  });

  const [showAllergyModal, setShowAllergyModal] = useState(false);
  const [newAllergy, setNewAllergy] = useState({
    allergen: '',
    reaction: '',
    severity: 'Moderate',
    status: 'Active',
  });

  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [newHistory, setNewHistory] = useState({
    condition_name: '',
    category: 'Chronic',
    onset_date: '',
    status: 'Active',
    notes: '',
  });

  const [editingVisit, setEditingVisit] = useState<Visit | null>(null);
  const [editVisitForm, setEditVisitForm] = useState({
    visit_type: 'OPD',
    chief_complaint: '',
    vitals_bp: '',
    vitals_hr: '',
    vitals_spo2: '',
    vitals_weight_kg: '',
    treatment_plan: '',
  });

  // New Visit Multi-Item Form State
  const [submittingVisit, setSubmittingVisit] = useState(false);
  const [visitForm, setVisitForm] = useState({
    visit_type: 'OPD',
    chief_complaint: '',
    vitals_bp: '120/80 mmHg',
    vitals_hr: '76',
    vitals_temp_c: '36.7',
    vitals_spo2: '99',
    vitals_weight_kg: '70.0',
    treatment_plan: '',
    note_type: 'SOAP',
    note_content: '',
    symptoms: [{ name: '', severity: 'Moderate', duration_days: 3, notes: '' }],
    diagnoses: [{ condition_name: '', icd10_code: '', status: 'Confirmed', notes: '' }],
    prescriptions: [{ medication_name: '', strength: '50mg', dosage: '1 tablet', frequency: 'Twice daily (BID)', duration_days: 14, instructions: '' }],
    test_results: [{ test_name: '', value: '', unit: '', reference_range: '', flag: 'Normal', result_date: new Date().toISOString().slice(0, 10) }],
  });
  const [extractingNote, setExtractingNote] = useState(false);

  // Sync light/dark theme attribute cleanly
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('medvault_theme', theme);
  }, [theme]);

  // Keyboard shortcuts: Escape closes overlays; '/' focuses patient search
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setInspectedCitation(null);
        setMobileMenuOpen(false);
        return;
      }
      if (e.key === '/') {
        const tag = (e.target as HTMLElement | null)?.tagName;
        if (tag !== 'INPUT' && tag !== 'TEXTAREA' && tag !== 'SELECT' && searchInputRef.current) {
          e.preventDefault();
          searchInputRef.current.focus();
        }
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const apiFetch = async (url: string, options: RequestInit = {}) => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
      handleLogout();
      throw new Error('Session expired. Sign in again to continue.');
    }
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      const detail = Array.isArray(errBody.detail)
        ? errBody.detail.map((d: any) => d.msg).join('; ')
        : errBody.detail;
      throw new Error(detail || `Request failed (${res.status})`);
    }
    return res.json();
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setAuthLoading(true);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Invalid email or password.');
      }
      const data = await res.json();
      sessionStorage.setItem('medvault_token', data.access_token);
      sessionStorage.setItem('medvault_user', JSON.stringify(data.user));
      setToken(data.access_token);
      setCurrentUser(data.user);
      setActiveNav('dashboard');
      setErrorMessage(null);
    } catch (err: any) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem('medvault_token');
    sessionStorage.removeItem('medvault_user');
    localStorage.removeItem('medvault_token');
    localStorage.removeItem('medvault_user');
    setToken(null);
    setCurrentUser(null);
    setSelectedPatient(null);
    setAiSummary(null);
    setStatusMessage(null);
    setErrorMessage(null);
    setMobileMenuOpen(false);
  };

  const loadDashboardAndCatalog = async () => {
    if (!token) return;
    setDashboardLoading(true);
    try {
      const [dashData, medsData] = await Promise.all([
        apiFetch('/api/dashboard/stats'),
        apiFetch('/api/patients/medications/catalog'),
      ]);
      setDashboard(dashData);
      setMedCatalog(medsData);
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setDashboardLoading(false);
    }
  };

  const loadPatientsList = async () => {
    if (!token) return;
    setPatientsLoading(true);
    try {
      const params = new URLSearchParams();
      if (patientSearch.trim()) params.set('q', patientSearch.trim());
      if (sexFilter) params.set('sex', sexFilter);
      if (bloodGroupFilter) params.set('blood_group', bloodGroupFilter);
      const data = await apiFetch(`/api/patients?${params.toString()}`);
      setPatients(data);
      setCurrentPage(1);
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setPatientsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadDashboardAndCatalog();
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      loadPatientsList();
    }
  }, [token, patientSearch, sexFilter, bloodGroupFilter]);

  const sortedPatients = useMemo(() => {
    const copy = [...patients];
    if (sortBy === 'name') {
      copy.sort((a, b) => `${a.first_name} ${a.last_name}`.localeCompare(`${b.first_name} ${b.last_name}`));
    } else if (sortBy === 'visits') {
      copy.sort((a, b) => b.visit_count - a.visit_count);
    } else if (sortBy === 'mrn') {
      copy.sort((a, b) => a.mrn.localeCompare(b.mrn));
    }
    return copy;
  }, [patients, sortBy]);

  const totalPages = Math.max(1, Math.ceil(sortedPatients.length / PAGE_SIZE));
  const pagedPatients = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return sortedPatients.slice(start, start + PAGE_SIZE);
  }, [sortedPatients, currentPage]);

  const filteredVisits = useMemo(() => {
    if (!selectedPatient) return [];
    const q = visitSearch.trim().toLowerCase();
    return selectedPatient.visits.filter((v) => {
      if (visitTypeFilter && v.visit_type !== visitTypeFilter) return false;
      if (!q) return true;
      const haystack = [
        `v-${v.id}`,
        v.chief_complaint,
        v.doctor_name || '',
        v.treatment_plan || '',
        ...v.symptoms.map((s) => s.name),
        ...v.diagnoses.map((d) => `${d.condition_name} ${d.icd10_code || ''}`),
        ...v.prescriptions.map((p) => p.medication?.name || ''),
        ...v.clinical_notes.map((n) => n.content),
      ]
        .join(' ')
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [selectedPatient, visitTypeFilter, visitSearch]);

  const filteredAuditLogs = useMemo(() => {
    const q = auditFilter.trim().toLowerCase();
    if (!q) return auditLogs;
    return auditLogs.filter((l) =>
      `${l.action} ${l.user_name} ${l.user_role} ${l.detail || ''}`.toLowerCase().includes(q)
    );
  }, [auditLogs, auditFilter]);

  const openPatientDetail = async (
    patientId: number,
    initialSubTab: 'timeline' | 'ai_summary' | 'ai_ask' | 'new_visit' = 'timeline',
    focusVisitId: number | null = null
  ) => {
    setErrorMessage(null);
    setMobileMenuOpen(false);
    try {
      const detail: PatientDetail = await apiFetch(`/api/patients/${patientId}`);
      setSelectedPatient(detail);
      setActiveNav('patient_detail');
      setPatientSubTab(initialSubTab);
      setQueryPatientScope(patientId);
      setHighlightedVisitId(focusVisitId);
      setVisitTypeFilter('');
      setVisitSearch('');
      setAiSummary(null);
      if (initialSubTab === 'ai_summary') {
        fetchPatientSummary(patientId, false);
      }
    } catch (err: any) {
      setErrorMessage(err.message);
    }
  };

  const fetchPatientSummary = async (patientId: number, forceRefresh = false) => {
    setSummaryLoading(true);
    setErrorMessage(null);
    try {
      const sum: AISummaryResponse = await apiFetch(
        `/api/ai/patients/${patientId}/summary?refresh=${forceRefresh}`
      );
      setAiSummary(sum);
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setSummaryLoading(false);
    }
  };

  const runNaturalLanguageQuery = async (customQuery?: string, customScope?: number | 'all') => {
    const qToRun = customQuery ?? nlQuery;
    const scopeToUse = customScope ?? queryPatientScope;
    if (!qToRun.trim()) {
      setErrorMessage('Enter a clinical question before running retrieval.');
      return;
    }
    setErrorMessage(null);
    setNlLoading(true);
    try {
      const res: AIQueryResponse = await apiFetch('/api/ai/query', {
        method: 'POST',
        body: JSON.stringify({
          query: qToRun,
          patient_id: scopeToUse === 'all' ? null : Number(scopeToUse),
        }),
      });
      setNlResult(res);
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setNlLoading(false);
    }
  };

  const handleCreatePatient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submittingPatient) return;
    setErrorMessage(null);
    setSubmittingPatient(true);
    try {
      const payload: any = {
        first_name: newPat.first_name,
        last_name: newPat.last_name,
        date_of_birth: newPat.date_of_birth,
        sex: newPat.sex,
        blood_group: newPat.blood_group || null,
        phone: newPat.phone,
        email: newPat.email || null,
        address: newPat.address || null,
        emergency_contact_name: newPat.emergency_contact_name || null,
        emergency_contact_phone: newPat.emergency_contact_phone || null,
        allergies: newPat.allergy_allergen.trim()
          ? [{ allergen: newPat.allergy_allergen, reaction: newPat.allergy_reaction || 'Hypersensitivity reaction', severity: 'Moderate', status: 'Active' }]
          : [],
        medical_history: newPat.history_condition.trim()
          ? [{ condition_name: newPat.history_condition, category: 'Chronic', status: 'Active' }]
          : [],
      };
      const created: PatientDetail = await apiFetch('/api/patients', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setShowNewPatientModal(false);
      setNewPat({
        first_name: '',
        last_name: '',
        date_of_birth: '1990-05-15',
        sex: 'Male',
        blood_group: 'O+',
        phone: '+91-98111-00000',
        email: '',
        address: '',
        emergency_contact_name: '',
        emergency_contact_phone: '',
        allergy_allergen: '',
        allergy_reaction: '',
        history_condition: '',
      });
      setStatusMessage(`Registered ${created.first_name} ${created.last_name} (${created.mrn}).`);
      await Promise.all([loadDashboardAndCatalog(), loadPatientsList()]);
      openPatientDetail(created.id, 'timeline');
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setSubmittingPatient(false);
    }
  };

  const openEditPatientModal = () => {
    if (!selectedPatient) return;
    setEditPat({
      first_name: selectedPatient.first_name,
      last_name: selectedPatient.last_name,
      date_of_birth: selectedPatient.date_of_birth,
      sex: selectedPatient.sex,
      blood_group: selectedPatient.blood_group || '',
      phone: selectedPatient.phone,
      email: selectedPatient.email || '',
      address: selectedPatient.address || '',
      emergency_contact_name: selectedPatient.emergency_contact_name || '',
      emergency_contact_phone: selectedPatient.emergency_contact_phone || '',
    });
    setShowEditPatientModal(true);
  };

  const handleUpdatePatient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatient || submittingPatient) return;
    setErrorMessage(null);
    setSubmittingPatient(true);
    try {
      const updated: PatientDetail = await apiFetch(`/api/patients/${selectedPatient.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          ...editPat,
          blood_group: editPat.blood_group || null,
          email: editPat.email || null,
          address: editPat.address || null,
          emergency_contact_name: editPat.emergency_contact_name || null,
          emergency_contact_phone: editPat.emergency_contact_phone || null,
        }),
      });
      setSelectedPatient(updated);
      setAiSummary(null);
      setShowEditPatientModal(false);
      setStatusMessage(`Updated demographic profile for ${updated.mrn}.`);
      await Promise.all([loadDashboardAndCatalog(), loadPatientsList()]);
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setSubmittingPatient(false);
    }
  };

  const handleAddAllergy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatient) return;
    setErrorMessage(null);
    try {
      await apiFetch(`/api/patients/${selectedPatient.id}/allergies`, {
        method: 'POST',
        body: JSON.stringify(newAllergy),
      });
      setShowAllergyModal(false);
      setNewAllergy({ allergen: '', reaction: '', severity: 'Moderate', status: 'Active' });
      setStatusMessage(`Recorded allergy alert for ${selectedPatient.mrn}.`);
      await Promise.all([
        openPatientDetail(selectedPatient.id, patientSubTab),
        loadDashboardAndCatalog(),
        loadPatientsList(),
      ]);
    } catch (err: any) {
      setErrorMessage(err.message);
    }
  };

  const handleAddHistory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatient) return;
    setErrorMessage(null);
    try {
      await apiFetch(`/api/patients/${selectedPatient.id}/history`, {
        method: 'POST',
        body: JSON.stringify({
          ...newHistory,
          onset_date: newHistory.onset_date || null,
          notes: newHistory.notes || null,
        }),
      });
      setShowHistoryModal(false);
      setNewHistory({ condition_name: '', category: 'Chronic', onset_date: '', status: 'Active', notes: '' });
      setStatusMessage(`Added baseline medical history entry for ${selectedPatient.mrn}.`);
      await Promise.all([
        openPatientDetail(selectedPatient.id, patientSubTab),
        loadPatientsList(),
      ]);
    } catch (err: any) {
      setErrorMessage(err.message);
    }
  };

  const openEditVisitModal = (v: Visit) => {
    setEditingVisit(v);
    setEditVisitForm({
      visit_type: v.visit_type,
      chief_complaint: v.chief_complaint,
      vitals_bp: v.vitals_bp || '',
      vitals_hr: v.vitals_hr ? String(v.vitals_hr) : '',
      vitals_spo2: v.vitals_spo2 ? String(v.vitals_spo2) : '',
      vitals_weight_kg: v.vitals_weight_kg || '',
      treatment_plan: v.treatment_plan || '',
    });
  };

  const handleUpdateVisit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingVisit || !selectedPatient) return;
    setErrorMessage(null);
    try {
      const updated = await apiFetch(`/api/patients/visits/${editingVisit.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          visit_type: editVisitForm.visit_type,
          chief_complaint: editVisitForm.chief_complaint,
          vitals_bp: editVisitForm.vitals_bp || null,
          vitals_hr: editVisitForm.vitals_hr ? Number(editVisitForm.vitals_hr) : null,
          vitals_spo2: editVisitForm.vitals_spo2 ? Number(editVisitForm.vitals_spo2) : null,
          vitals_weight_kg: editVisitForm.vitals_weight_kg || null,
          treatment_plan: editVisitForm.treatment_plan || null,
        }),
      });
      setEditingVisit(null);
      setStatusMessage(`Updated visit [V-${updated.id}].`);
      await openPatientDetail(selectedPatient.id, 'timeline', updated.id);
    } catch (err: any) {
      setErrorMessage(err.message);
    }
  };

  const handleAutoExtractFromNote = async () => {
    if (!visitForm.note_content.trim()) {
      setErrorMessage('Enter a consultation note before running entity extraction.');
      return;
    }
    setErrorMessage(null);
    setExtractingNote(true);
    try {
      const extracted = await apiFetch('/api/ai/extract-note', {
        method: 'POST',
        body: JSON.stringify({ note_text: visitForm.note_content }),
      });
      setVisitForm((prev) => ({
        ...prev,
        chief_complaint: prev.chief_complaint || extracted.chief_complaint,
        treatment_plan: prev.treatment_plan || extracted.recommended_follow_up,
        symptoms:
          extracted.extracted_symptoms.length > 0
            ? extracted.extracted_symptoms.map((s: any) => ({
                name: s.name,
                severity: s.severity || 'Moderate',
                duration_days: 3,
                notes: 'Extracted from clinical note',
              }))
            : prev.symptoms,
        diagnoses:
          extracted.suspected_diagnoses.length > 0
            ? extracted.suspected_diagnoses.map((d: any) => ({
                condition_name: d.condition_name,
                icd10_code: d.icd10_code || '',
                status: d.status || 'Provisional',
                notes: 'Candidate diagnosis extracted from note',
              }))
            : prev.diagnoses,
        prescriptions:
          extracted.mentioned_medications.length > 0
            ? extracted.mentioned_medications.map((m: any) => ({
                medication_name: m.medication.split(' ')[0],
                strength: m.medication.split(' ')[1] || 'Standard',
                dosage: '1 dose',
                frequency: m.dosage_notes || 'As directed',
                duration_days: 14,
                instructions: 'Extracted from consultation note',
              }))
            : prev.prescriptions,
      }));
      setStatusMessage(extracted.concise_summary);
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setExtractingNote(false);
    }
  };

  const handleCreateVisit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatient || submittingVisit) return;
    setErrorMessage(null);
    setSubmittingVisit(true);
    try {
      const payload = {
        visit_type: visitForm.visit_type,
        chief_complaint: visitForm.chief_complaint,
        vitals_bp: visitForm.vitals_bp || null,
        vitals_hr: visitForm.vitals_hr ? Number(visitForm.vitals_hr) : null,
        vitals_temp_c: visitForm.vitals_temp_c || null,
        vitals_spo2: visitForm.vitals_spo2 ? Number(visitForm.vitals_spo2) : null,
        vitals_weight_kg: visitForm.vitals_weight_kg || null,
        treatment_plan: visitForm.treatment_plan || null,
        symptoms: visitForm.symptoms.filter((s) => s.name.trim() !== ''),
        diagnoses: visitForm.diagnoses.filter((d) => d.condition_name.trim() !== ''),
        prescriptions: visitForm.prescriptions.filter((p) => p.medication_name.trim() !== ''),
        clinical_notes: visitForm.note_content.trim()
          ? [{ note_type: visitForm.note_type, content: visitForm.note_content }]
          : [],
        test_results: visitForm.test_results.filter((t) => t.test_name.trim() !== '' && t.value.trim() !== ''),
      };
      const savedVisit = await apiFetch(`/api/patients/${selectedPatient.id}/visits`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setStatusMessage(`Saved encounter [V-${savedVisit.id}] for ${selectedPatient.mrn}.`);
      setVisitForm({
        visit_type: 'OPD',
        chief_complaint: '',
        vitals_bp: '120/80 mmHg',
        vitals_hr: '76',
        vitals_temp_c: '36.7',
        vitals_spo2: '99',
        vitals_weight_kg: '70.0',
        treatment_plan: '',
        note_type: 'SOAP',
        note_content: '',
        symptoms: [{ name: '', severity: 'Moderate', duration_days: 3, notes: '' }],
        diagnoses: [{ condition_name: '', icd10_code: '', status: 'Confirmed', notes: '' }],
        prescriptions: [{ medication_name: '', strength: '50mg', dosage: '1 tablet', frequency: 'Twice daily (BID)', duration_days: 14, instructions: '' }],
        test_results: [{ test_name: '', value: '', unit: '', reference_range: '', flag: 'Normal', result_date: new Date().toISOString().slice(0, 10) }],
      });
      await Promise.all([loadDashboardAndCatalog(), loadPatientsList()]);
      await openPatientDetail(selectedPatient.id, 'timeline', savedVisit.id);
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setSubmittingVisit(false);
    }
  };

  const loadAuditLogs = async () => {
    try {
      const logs = await apiFetch('/api/auth/audit-logs?limit=60');
      setAuditLogs(logs);
    } catch (err: any) {
      setErrorMessage(err.message);
    }
  };

  const toggleClaimFlag = (key: string) => {
    setFlaggedClaims((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const flaggedCountForCurrentPatient = useMemo(() => {
    if (!selectedPatient) return 0;
    const prefix = `p${selectedPatient.id}:`;
    return Object.entries(flaggedClaims).filter(([k, v]) => k.startsWith(prefix) && v).length;
  }, [flaggedClaims, selectedPatient]);

  const renderCitationBadges = (citations: string[], indexMap: Record<string, CitationRef>) => {
    if (!citations || citations.length === 0) return null;
    return (
      <span className="inline-flex flex-wrap gap-1.5 ml-2 align-middle">
        {citations.map((tag) => {
          const ref = indexMap[tag];
          return (
            <button
              key={tag}
              type="button"
              onClick={() => {
                if (ref) {
                  setInspectedCitation(ref);
                  if (ref.visit_id) {
                    setHighlightedVisitId(ref.visit_id);
                  }
                }
              }}
              aria-label={`Inspect source record ${tag}`}
              title={ref ? `${ref.label}: ${ref.snippet}` : tag}
              className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-mono tabular-nums font-semibold bg-[#EFDFC5] text-[#380F17] border border-[#C9B08B] hover:bg-[#8F0B13] hover:text-white hover:border-[#8F0B13] transition-colors"
            >
              [{tag}]
            </button>
          );
        })}
      </span>
    );
  };

  const renderFlagButton = (claimKey: string) => {
    const isFlagged = Boolean(flaggedClaims[claimKey]);
    return (
      <button
        type="button"
        onClick={() => toggleClaimFlag(claimKey)}
        aria-pressed={isFlagged}
        title="Mark this statement for clinician verification"
        className={`mt-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold border transition-colors ${
          isFlagged
            ? 'bg-[var(--status-critical-bg)] text-[var(--status-critical-fg)] border-[var(--status-critical-border)]'
            : 'bg-surface text-ink-muted border-border-warm hover:text-[#8F0B13] hover:border-[#8F0B13]/40'
        }`}
      >
        <Flag className="w-3 h-3" />
        {isFlagged ? 'Flagged for Review' : 'Flag Issue'}
      </button>
    );
  };

  const breadcrumbText = useMemo(() => {
    if (activeNav === 'dashboard') return 'Workspace / Clinical Dashboard';
    if (activeNav === 'patients') return 'Workspace / Patient Registry';
    if (activeNav === 'ai_retrieval') return 'Workspace / AI Historical Retrieval';
    if (activeNav === 'audit') return 'Workspace / Access & Audit Trail';
    if (activeNav === 'patient_detail' && selectedPatient) {
      const tabLabel =
        patientSubTab === 'timeline'
          ? 'Clinical Timeline'
          : patientSubTab === 'ai_summary'
          ? 'AI Summary'
          : patientSubTab === 'ai_ask'
          ? 'Historical Query'
          : 'New Visit Entry';
      return `Workspace / Patients / ${selectedPatient.first_name} ${selectedPatient.last_name} (${selectedPatient.mrn}) / ${tabLabel}`;
    }
    return 'Workspace';
  }, [activeNav, patientSubTab, selectedPatient]);

  // ============================================================================
  // LOGIN SCREEN
  // ============================================================================
  if (!token || !currentUser) {
    return (
      <div className="min-h-screen bg-[#FAF8F5] dark:bg-[#151213] flex items-center justify-center p-4 sm:p-6">
        <div className="max-w-5xl w-full grid grid-cols-1 lg:grid-cols-12 bg-surface rounded-xl overflow-hidden border border-border-warm shadow-xl">
          {/* Left Burgundy Editorial Brand Column */}
          <div className="lg:col-span-7 bg-[#380F17] text-[#FAF8F5] p-8 sm:p-10 flex flex-col justify-between">
            <div>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-[#8F0B13] flex items-center justify-center text-[#EFDFC5]">
                    <HeartPulse className="w-5 h-5" />
                  </div>
                  <h1 className="font-serif text-3xl sm:text-4xl font-semibold tracking-[-0.02em]">
                    MedVault <span className="text-[#EFDFC5]">AI</span>
                  </h1>
                </div>
                <span className="px-2.5 py-1 rounded-full bg-[#EFDFC5]/15 border border-[#EFDFC5]/30 text-[#EFDFC5] text-[11px] font-mono">
                  3NF Clinical EHR
                </span>
              </div>

              <p className="mt-4 text-[#EFDFC5]/85 text-sm leading-relaxed max-w-xl">
                Store patient encounter histories inside a 13-table normalised database and review records through citation-verified AI synthesis and structured retrieval.
              </p>

              <div className="mt-8 space-y-3">
                <div className="flex items-start gap-3.5 bg-[#2A0B11] border border-[#561925] rounded-xl p-4">
                  <Database className="w-5 h-5 text-[#EFDFC5] shrink-0 mt-0.5" />
                  <div>
                    <h2 className="text-sm font-semibold text-white">Normalised Relational Storage</h2>
                    <p className="text-xs text-[#EFDFC5]/75 mt-0.5 leading-relaxed">
                      Patients, Visits, Symptoms, ICD-10 Diagnoses, Prescriptions, Medications, SOAP Notes, Allergies, Labs, and Audit Logs.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3.5 bg-[#2A0B11] border border-[#561925] rounded-xl p-4">
                  <Sparkles className="w-5 h-5 text-[#EFDFC5] shrink-0 mt-0.5" />
                  <div>
                    <h2 className="text-sm font-semibold text-white">Citation-Verified AI Summaries</h2>
                    <p className="text-xs text-[#EFDFC5]/75 mt-0.5 leading-relaxed">
                      Every generated summary links directly to stored primary keys (<code className="text-[#EFDFC5] font-mono">[V-1]</code>, <code className="text-[#EFDFC5] font-mono">[DX-3]</code>) and flags unrecorded data explicitly.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3.5 bg-[#2A0B11] border border-[#561925] rounded-xl p-4">
                  <ShieldCheck className="w-5 h-5 text-[#EFDFC5] shrink-0 mt-0.5" />
                  <div>
                    <h2 className="text-sm font-semibold text-white">Role Access Control &amp; Audit Trail</h2>
                    <p className="text-xs text-[#EFDFC5]/75 mt-0.5 leading-relaxed">
                      Bcrypt credential verification, session-scoped JWT tokens, and clinical action logging.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-8 pt-6 border-t border-[#561925] flex flex-wrap items-center justify-between gap-4 text-xs text-[#EFDFC5]/75">
              <div>
                <span className="font-semibold text-[#EFDFC5]">Authors:</span> Pushkar Panwar (2501730022) &middot; Saksham Singh (2501730270)
              </div>
              <a
                href="/presentation.html"
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1 rounded-lg bg-[#8F0B13] hover:bg-[#74080F] text-white font-mono text-[11px] transition-colors"
              >
                Presentation Deck
              </a>
            </div>
          </div>

          {/* Right Form Column */}
          <div className="lg:col-span-5 p-8 sm:p-10 flex flex-col justify-center bg-surface">
            <div className="mb-6">
              <h2 className="font-serif text-2xl font-semibold text-ink-primary">Clinician Sign In</h2>
              <p className="text-xs text-ink-secondary mt-1">
                Choose a demo account preset or enter institutional credentials.
              </p>
            </div>

            <div className="mb-5">
              <span className="block text-[11px] font-semibold uppercase tracking-wider text-ink-muted mb-2">
                Demo Credentials
              </span>
              <div className="grid grid-cols-1 gap-2">
                {[
                  { name: 'Dr. Ananya Sharma, MD', sub: 'Internal Medicine', mail: 'dr.sharma@medvault.edu', pw: 'Doctor@123', role: 'Doctor' },
                  { name: 'Dr. Rajesh Verma, DM', sub: 'Neurology', mail: 'dr.verma@medvault.edu', pw: 'Doctor@123', role: 'Doctor' },
                  { name: 'Pushkar Panwar', sub: 'System Administrator', mail: 'admin@medvault.edu', pw: 'Admin@123', role: 'Admin' },
                ].map((preset) => {
                  const selected = email === preset.mail;
                  return (
                    <button
                      key={preset.mail}
                      type="button"
                      onClick={() => {
                        setEmail(preset.mail);
                        setPassword(preset.pw);
                      }}
                      className={`text-left px-3.5 py-2.5 rounded-lg border text-xs transition-colors flex items-center justify-between ${
                        selected
                          ? 'border-[#8F0B13] bg-surface-ivory text-[#380F17] dark:text-[#EFDFC5] font-semibold'
                          : 'border-border-warm hover:border-[#8F0B13]/50 text-ink-primary'
                      }`}
                    >
                      <div>
                        <div className="font-semibold">{preset.name}</div>
                        <div className="text-[11px] text-ink-secondary">
                          {preset.sub} &middot; {preset.mail}
                        </div>
                      </div>
                      <Badge variant={preset.role === 'Admin' ? 'brand' : 'crimson'}>{preset.role}</Badge>
                    </button>
                  );
                })}
              </div>
            </div>

            {authError && <AlertBanner variant="error" message={authError} className="mb-4" />}

            <form onSubmit={handleLogin} className="space-y-4">
              <Input
                id="login-email"
                label="Institutional Email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <Input
                id="login-password"
                label="Password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <Button
                type="submit"
                variant="primary"
                size="lg"
                loading={authLoading}
                className="w-full"
              >
                <Lock className="w-4 h-4" />
                {authLoading ? 'Authenticating...' : 'Access Clinical Workspace'}
              </Button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  // Shared Sidebar Content (used on Desktop & Mobile Drawer)
  const sidebarBody = (
    <div className="flex flex-col justify-between h-full bg-[var(--bg-sidebar)] text-[#FAF8F5]">
      <div>
        <div className="p-5 border-b border-[#561925] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#8F0B13] flex items-center justify-center text-[#EFDFC5]">
              <HeartPulse className="w-5 h-5" />
            </div>
            <div>
              <div className="font-serif font-semibold text-white tracking-tight text-lg leading-none">
                MedVault AI
              </div>
              <div className="text-[11px] text-[#EFDFC5]/75 font-mono mt-1">Clinical Record DB</div>
            </div>
          </div>
          <button
            type="button"
            aria-label="Close navigation menu"
            onClick={() => setMobileMenuOpen(false)}
            className="lg:hidden p-1.5 rounded-lg text-[#EFDFC5]/80 hover:bg-[#4C1620]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <nav aria-label="Primary clinical navigation" className="p-3 space-y-1">
          {[
            { id: 'dashboard' as const, label: 'Clinical Dashboard', icon: Activity },
            { id: 'patients' as const, label: 'Patients & EHR Directory', icon: Users },
            { id: 'ai_retrieval' as const, label: 'AI Historical Retrieval', icon: Sparkles },
            { id: 'audit' as const, label: 'RBAC & Audit Trail', icon: ShieldCheck },
          ].map((item) => {
            const Icon = item.icon;
            const active =
              activeNav === item.id || (item.id === 'patients' && activeNav === 'patient_detail');
            return (
              <button
                key={item.id}
                type="button"
                aria-current={active ? 'page' : undefined}
                onClick={() => {
                  setActiveNav(item.id);
                  setMobileMenuOpen(false);
                  if (item.id === 'ai_retrieval' && !nlResult) {
                    runNaturalLanguageQuery();
                  }
                  if (item.id === 'audit') {
                    loadAuditLogs();
                  }
                }}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-semibold transition-colors ${
                  active
                    ? 'bg-[#8F0B13] text-white'
                    : 'text-[#EFDFC5]/80 hover:bg-[var(--bg-sidebar-hover)] hover:text-white'
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="mt-4 px-4">
          <div className="flex items-center justify-between text-[11px] font-semibold uppercase tracking-wider text-[#EFDFC5]/65 mb-2">
            <span>Quick Patient Access</span>
            <button
              type="button"
              onClick={() => {
                setMobileMenuOpen(false);
                setShowNewPatientModal(true);
              }}
              className="text-[#EFDFC5] hover:underline flex items-center gap-0.5"
            >
              <Plus className="w-3.5 h-3.5" /> New
            </button>
          </div>
          <div className="space-y-1 max-h-60 overflow-y-auto pr-1">
            {patients.slice(0, 8).map((p) => {
              const isSelected = selectedPatient?.id === p.id && activeNav === 'patient_detail';
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => openPatientDetail(p.id, 'timeline')}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors flex items-center justify-between ${
                    isSelected
                      ? 'bg-[#4C1620] text-[#EFDFC5] font-semibold border border-[#8F0B13]'
                      : 'text-[#EFDFC5]/75 hover:bg-[var(--bg-sidebar-hover)] hover:text-white'
                  }`}
                >
                  <div className="truncate pr-2">
                    <div className="truncate">{p.first_name} {p.last_name}</div>
                    <div className="text-[10px] font-mono tabular-nums text-[#EFDFC5]/55">{p.mrn}</div>
                  </div>
                  <span className="text-[10px] font-mono tabular-nums px-1.5 py-0.5 rounded bg-[#2A0B11] text-[#EFDFC5]">
                    {p.visit_count}v
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-[#561925] bg-[#2A0B11]">
        <div className="flex items-center justify-between">
          <div className="truncate pr-2">
            <div className="text-xs font-semibold text-white truncate">{currentUser.full_name}</div>
            <div className="text-[11px] text-[#EFDFC5]/80 uppercase font-mono">
              Role: {currentUser.role_name}
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            aria-label="Sign out of MedVault AI"
            title="Sign Out"
            className="p-2 rounded-lg text-[#EFDFC5]/75 hover:text-white hover:bg-[#4C1620] transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
        <div className="mt-3 pt-2.5 border-t border-[#561925] text-[10px] text-[#EFDFC5]/60 leading-tight font-mono tabular-nums">
          Pushkar Panwar (2501730022)<br />
          Saksham Singh (2501730270)
        </div>
      </div>
    </div>
  );

  // ============================================================================
  // AUTHENTICATED APPLICATION SHELL
  // ============================================================================
  return (
    <div className="min-h-screen flex bg-canvas text-ink-primary">
      {/* Desktop Burgundy Sidebar */}
      <aside className="hidden lg:flex w-64 shrink-0 border-r border-[#561925] flex-col">
        {sidebarBody}
      </aside>

      {/* Mobile Slide-Over Drawer */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-50 lg:hidden bg-black/55 flex"
          onClick={(e) => {
            if (e.target === e.currentTarget) setMobileMenuOpen(false);
          }}
        >
          <aside className="w-72 max-w-[85vw] h-full shadow-2xl">{sidebarBody}</aside>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Clinical Header Bar */}
        <header className="bg-surface border-b border-border-warm px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              aria-label="Open navigation menu"
              onClick={() => setMobileMenuOpen(true)}
              className="lg:hidden p-2 rounded-lg border border-border-warm text-ink-primary hover:bg-surface-muted"
            >
              <Menu className="w-4 h-4" />
            </button>
            <div className="min-w-0">
              <div className="text-[11px] font-mono text-ink-secondary truncate" aria-label="Breadcrumb">
                {breadcrumbText}
              </div>
              <div className="flex flex-wrap items-center gap-2 mt-1">
                <Badge variant="warning">
                  <ShieldAlert className="w-3 h-3" />
                  Synthetic Data Sandbox
                </Badge>
                <Badge variant="ivory" className="hidden sm:inline-flex">
                  <CheckCircle2 className="w-3 h-3" />
                  Citation Guardrails Active
                </Badge>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="secondary"
              size="sm"
              aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
              onClick={() => setTheme((prev) => (prev === 'light' ? 'dark' : 'light'))}
            >
              {theme === 'light' ? <Moon className="w-3.5 h-3.5" /> : <Sun className="w-3.5 h-3.5" />}
              <span className="hidden sm:inline">{theme === 'light' ? 'Dark' : 'Light'}</span>
            </Button>

            <a
              href="/presentation.html"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border-warm bg-surface hover:bg-surface-muted text-ink-primary text-xs font-semibold transition-colors"
            >
              <Presentation className="w-3.5 h-3.5 text-[#8F0B13]" />
              Slides
            </a>

            <Button variant="primary" size="sm" onClick={() => setShowNewPatientModal(true)}>
              <UserPlus className="w-3.5 h-3.5" />
              Register Patient
            </Button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          {errorMessage && (
            <div className="max-w-7xl mx-auto mb-5">
              <AlertBanner
                variant="error"
                message={errorMessage}
                onDismiss={() => setErrorMessage(null)}
              />
            </div>
          )}

          {statusMessage && (
            <div className="max-w-7xl mx-auto mb-5">
              <AlertBanner
                variant="success"
                message={statusMessage}
                onDismiss={() => setStatusMessage(null)}
              />
            </div>
          )}

          {/* ================================================================
              VIEW 1: DASHBOARD
          ================================================================ */}
          {activeNav === 'dashboard' && dashboardLoading && !dashboard && (
            <div className="max-w-7xl mx-auto space-y-6" aria-label="Loading clinical dashboard">
              <SkeletonBlock className="h-10 w-72" />
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <SkeletonBlock className="h-28" />
                <SkeletonBlock className="h-28" />
                <SkeletonBlock className="h-28" />
                <SkeletonBlock className="h-28" />
              </div>
              <SkeletonBlock className="h-72" />
            </div>
          )}

          {activeNav === 'dashboard' && dashboard && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h1 className="font-serif text-2xl sm:text-3xl font-semibold tracking-[-0.02em] text-ink-primary">
                    Clinical Intelligence Dashboard
                  </h1>
                  <p className="text-xs sm:text-sm text-ink-secondary mt-0.5">
                    Live relational database counts, SQL diagnostic aggregations, and patient history access.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="brand"
                    onClick={() => {
                      setActiveNav('ai_retrieval');
                      runNaturalLanguageQuery();
                    }}
                  >
                    <Sparkles className="w-4 h-4" />
                    Ask AI Across Records
                  </Button>
                </div>
              </div>

              {/* 4 KPI Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="p-5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-secondary">
                      Registered Patients
                    </span>
                    <div className="p-2 rounded-lg bg-[#380F17]/10 text-[#380F17] dark:bg-[#EFDFC5]/10 dark:text-[#EFDFC5]">
                      <Users className="w-4 h-4" />
                    </div>
                  </div>
                  <div className="mt-3 text-3xl font-bold tabular-nums text-ink-primary">
                    {dashboard.counts.total_patients}
                  </div>
                  <div className="mt-1 text-xs text-ink-secondary">Active MRN profiles</div>
                </Card>

                <Card className="p-5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-secondary">
                      Total Medical Records
                    </span>
                    <div className="p-2 rounded-lg bg-[#8F0B13]/10 text-[#8F0B13] dark:text-[#FCA5A5]">
                      <Database className="w-4 h-4" />
                    </div>
                  </div>
                  <div className="mt-3 text-3xl font-bold tabular-nums text-ink-primary">
                    {dashboard.counts.total_medical_records}
                  </div>
                  <div className="mt-1 text-xs text-ink-secondary tabular-nums">
                    {dashboard.counts.total_visits} visits &middot; {dashboard.counts.total_diagnoses} dx &middot; {dashboard.counts.total_prescriptions} rx
                  </div>
                </Card>

                <Card className="p-5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-secondary">
                      Notes &amp; Lab Panels
                    </span>
                    <div className="p-2 rounded-lg bg-surface-ivory text-[#380F17] dark:text-[#EFDFC5]">
                      <Microscope className="w-4 h-4" />
                    </div>
                  </div>
                  <div className="mt-3 text-3xl font-bold tabular-nums text-ink-primary">
                    {dashboard.counts.total_clinical_notes + dashboard.counts.total_lab_results}
                  </div>
                  <div className="mt-1 text-xs text-ink-secondary tabular-nums">
                    {dashboard.counts.total_clinical_notes} SOAP notes &middot; {dashboard.counts.total_lab_results} lab tests
                  </div>
                </Card>

                <Card className="p-5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-secondary">
                      Active Allergy Alerts
                    </span>
                    <div className="p-2 rounded-lg bg-[var(--status-critical-bg)] text-[var(--status-critical-fg)]">
                      <AlertTriangle className="w-4 h-4" />
                    </div>
                  </div>
                  <div className="mt-3 text-3xl font-bold tabular-nums text-ink-primary">
                    {dashboard.counts.total_allergies}
                  </div>
                  <div className="mt-1 text-xs text-ink-secondary">Cross-checked in AI summaries</div>
                </Card>
              </div>

              {/* Search Launcher + SQL Visual Distribution Bars */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <Card className="lg:col-span-7 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h2 className="text-base font-bold text-ink-primary">
                        Quick Patient Search &amp; AI Summary Launcher
                      </h2>
                      <p className="text-xs text-ink-secondary">
                        Press <kbd className="px-1.5 py-0.5 rounded bg-surface-muted border border-border-warm font-mono text-[10px]">/</kbd> to filter by name, MRN, phone, or diagnosis.
                      </p>
                    </div>
                  </div>

                  <div className="relative mb-4">
                    <Search className="w-4 h-4 text-ink-muted absolute left-3.5 top-2.5" />
                    <Input
                      ref={searchInputRef}
                      id="dashboard-patient-search"
                      aria-label="Filter patients by name, MRN, or condition"
                      value={patientSearch}
                      onChange={(e) => setPatientSearch(e.target.value)}
                      placeholder="Filter patients (e.g. Aarav, MRN-2026-00001, Migraine, Diabetes)..."
                      className="pl-10"
                    />
                  </div>

                  {patientsLoading ? (
                    <div className="space-y-2.5">
                      <SkeletonBlock className="h-16" />
                      <SkeletonBlock className="h-16" />
                    </div>
                  ) : patients.length === 0 ? (
                    <EmptyState
                      title={`No patients match "${patientSearch}"`}
                      description="Clear the search filter or register a new synthetic patient profile."
                      actionLabel="Reset Search & Filters"
                      onAction={() => {
                        setPatientSearch('');
                        setSexFilter('');
                        setBloodGroupFilter('');
                      }}
                    />
                  ) : (
                    <div className="space-y-2.5">
                      {patients.slice(0, 6).map((p) => (
                        <div
                          key={p.id}
                          className="p-3.5 rounded-xl border border-border-warm hover:border-[#8F0B13] bg-surface-muted/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-colors"
                        >
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-bold text-sm text-ink-primary">
                                {p.first_name} {p.last_name}
                              </span>
                              <Badge variant="mono">{p.mrn}</Badge>
                              <span className="text-xs text-ink-secondary">
                                {p.sex} &middot; {p.blood_group || 'BG Missing'}
                              </span>
                            </div>
                            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                              {p.primary_conditions.slice(0, 2).map((c, idx) => (
                                <Badge key={idx} variant="ivory">
                                  {c}
                                </Badge>
                              ))}
                              {p.active_allergies.map((alg, idx) => (
                                <Badge key={idx} variant="critical">
                                  Allergy: {alg}
                                </Badge>
                              ))}
                            </div>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => openPatientDetail(p.id, 'timeline')}
                              className="tabular-nums"
                            >
                              Records ({p.visit_count})
                            </Button>
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => openPatientDetail(p.id, 'ai_summary')}
                            >
                              <Sparkles className="w-3.5 h-3.5" />
                              AI Summary
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>

                <div className="lg:col-span-5 space-y-6">
                  {/* Top Diagnoses Distribution Bars */}
                  <Card className="p-6">
                    <h2 className="text-base font-bold text-ink-primary mb-1">
                      Prevalent Diagnoses (SQL GROUP BY)
                    </h2>
                    <p className="text-xs text-ink-secondary mb-4">
                      Active or confirmed diagnoses across all patient visits.
                    </p>
                    <div className="space-y-3">
                      {dashboard.top_conditions.map((item, idx) => {
                        const max = dashboard.top_conditions[0]?.count || 1;
                        const pct = Math.max(12, Math.round((item.count / max) * 100));
                        return (
                          <div key={idx} className="space-y-1 text-xs">
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-medium text-ink-primary truncate">{item.condition}</span>
                              <span className="font-mono tabular-nums text-ink-secondary shrink-0">
                                {item.count} dx
                              </span>
                            </div>
                            <div className="h-2 rounded-full bg-surface-muted overflow-hidden">
                              <div
                                className="h-full rounded-full bg-[#8F0B13]"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </Card>

                  {/* Top Symptoms Distribution Bars */}
                  <Card className="p-6">
                    <h2 className="text-base font-bold text-ink-primary mb-3">
                      Recurring Symptoms (SQL GROUP BY)
                    </h2>
                    <div className="space-y-3">
                      {dashboard.top_symptoms.map((item, idx) => {
                        const max = dashboard.top_symptoms[0]?.count || 1;
                        const pct = Math.max(12, Math.round((item.count / max) * 100));
                        return (
                          <div key={idx} className="space-y-1 text-xs">
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-medium text-ink-primary truncate">{item.symptom}</span>
                              <span className="font-mono tabular-nums text-[#380F17] dark:text-[#EFDFC5] font-semibold shrink-0">
                                {item.count} visits
                              </span>
                            </div>
                            <div className="h-2 rounded-full bg-surface-muted overflow-hidden">
                              <div
                                className="h-full rounded-full bg-[#380F17] dark:bg-[#EFDFC5]"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </Card>
                </div>
              </div>

              {/* Recent Clinical Visits Table */}
              <Card className="overflow-hidden">
                <div className="p-5 border-b border-border-warm flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="text-base font-bold text-ink-primary">Recent Patient Encounters</h2>
                    <p className="text-xs text-ink-secondary">
                      Select an encounter row to inspect its linked symptoms, diagnoses, prescriptions, and lab panels.
                    </p>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-[#380F17] text-[#EFDFC5] text-[11px] font-semibold uppercase tracking-wider">
                        <th className="py-3 px-4">Visit Tag</th>
                        <th className="py-3 px-4">Date</th>
                        <th className="py-3 px-4">Patient</th>
                        <th className="py-3 px-4">Type</th>
                        <th className="py-3 px-4">Chief Complaint</th>
                        <th className="py-3 px-4">Primary Diagnosis</th>
                        <th className="py-3 px-4">Attending Clinician</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-warm text-xs">
                      {dashboard.recent_visits.map((v) => (
                        <tr
                          key={v.visit_id}
                          tabIndex={0}
                          onClick={() => openPatientDetail(v.patient_id, 'timeline', v.visit_id)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              openPatientDetail(v.patient_id, 'timeline', v.visit_id);
                            }
                          }}
                          className="hover:bg-surface-ivory/60 cursor-pointer transition-colors"
                        >
                          <td className="py-3 px-4 font-mono tabular-nums font-semibold text-[#8F0B13] dark:text-[#EFDFC5]">
                            [{v.visit_tag}]
                          </td>
                          <td className="py-3 px-4 font-mono tabular-nums text-ink-secondary whitespace-nowrap">
                            {v.visit_date.slice(0, 10)}
                          </td>
                          <td className="py-3 px-4 font-semibold text-ink-primary">
                            {v.patient_name}{' '}
                            <span className="font-mono tabular-nums text-[11px] text-ink-muted">
                              ({v.patient_mrn})
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <Badge variant="neutral">{v.visit_type}</Badge>
                          </td>
                          <td className="py-3 px-4 text-ink-primary max-w-xs truncate">{v.chief_complaint}</td>
                          <td className="py-3 px-4 font-medium text-ink-primary">{v.primary_diagnosis}</td>
                          <td className="py-3 px-4 text-ink-secondary">{v.doctor_name}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}

          {/* ================================================================
              VIEW 2: PATIENTS DIRECTORY (WITH SORTING, FILTERS, PAGINATION)
          ================================================================ */}
          {activeNav === 'patients' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h1 className="font-serif text-2xl sm:text-3xl font-semibold tracking-[-0.02em] text-ink-primary">
                    Patient Registry &amp; EHR Directory
                  </h1>
                  <p className="text-xs sm:text-sm text-ink-secondary mt-0.5">
                    Search, filter, sort, and inspect registered patient profiles ({sortedPatients.length} matched).
                  </p>
                </div>
                <Button variant="primary" onClick={() => setShowNewPatientModal(true)}>
                  <UserPlus className="w-4 h-4" />
                  Register New Patient
                </Button>
              </div>

              <Card className="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-3">
                <div className="relative lg:col-span-5">
                  <Search className="w-4 h-4 text-ink-muted absolute left-3.5 top-2.5" />
                  <Input
                    ref={searchInputRef}
                    id="directory-search"
                    aria-label="Search patients by name, MRN, phone, or diagnosis"
                    value={patientSearch}
                    onChange={(e) => setPatientSearch(e.target.value)}
                    placeholder="Search name, MRN, phone, or condition..."
                    className="pl-10"
                  />
                </div>
                <div className="lg:col-span-2">
                  <Select
                    id="directory-sex-filter"
                    aria-label="Filter by sex"
                    value={sexFilter}
                    onChange={(e) => setSexFilter(e.target.value)}
                  >
                    <option value="">All Sexes</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </Select>
                </div>
                <div className="lg:col-span-2">
                  <Select
                    id="directory-bg-filter"
                    aria-label="Filter by blood group"
                    value={bloodGroupFilter}
                    onChange={(e) => setBloodGroupFilter(e.target.value)}
                  >
                    <option value="">All Blood Groups</option>
                    {BLOOD_GROUPS.map((bg) => (
                      <option key={bg} value={bg}>
                        {bg}
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="lg:col-span-3">
                  <Select
                    id="directory-sort"
                    aria-label="Sort patients"
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as any)}
                  >
                    <option value="updated">Sort: Recently Updated</option>
                    <option value="name">Sort: Patient Name (A-Z)</option>
                    <option value="visits">Sort: Most Clinical Visits</option>
                    <option value="mrn">Sort: MRN Order</option>
                  </Select>
                </div>
              </Card>

              {patientsLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <SkeletonBlock className="h-48" />
                  <SkeletonBlock className="h-48" />
                </div>
              ) : pagedPatients.length === 0 ? (
                <EmptyState
                  title="No patient profiles match your filters"
                  description="Adjust the search text, sex, or blood group filter to view matching patient records."
                  actionLabel="Reset Search & Filters"
                  onAction={() => {
                    setPatientSearch('');
                    setSexFilter('');
                    setBloodGroupFilter('');
                  }}
                />
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {pagedPatients.map((p) => (
                      <Card
                        key={p.id}
                        className="p-5 hover:border-[#8F0B13] transition-colors flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="flex flex-wrap items-center gap-2">
                                <h3 className="text-base font-bold text-ink-primary">
                                  {p.first_name} {p.last_name}
                                </h3>
                                <Badge variant="mono">{p.mrn}</Badge>
                              </div>
                              <div className="text-xs text-ink-secondary mt-1 tabular-nums">
                                DOB: {p.date_of_birth} &middot; {p.sex} &middot; Blood:{' '}
                                <strong className="text-ink-primary">{p.blood_group || 'Missing'}</strong> &middot; {p.phone}
                              </div>
                            </div>
                            <Badge variant="crimson" className="tabular-nums shrink-0">
                              {p.visit_count} Visits
                            </Badge>
                          </div>

                          <div className="mt-4 space-y-2">
                            <div>
                              <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted block mb-1">
                                Documented Conditions
                              </span>
                              <div className="flex flex-wrap gap-1.5">
                                {p.primary_conditions.length > 0 ? (
                                  p.primary_conditions.map((c, idx) => (
                                    <Badge key={idx} variant="ivory">
                                      {c}
                                    </Badge>
                                  ))
                                ) : (
                                  <span className="text-xs text-ink-muted italic">No conditions recorded</span>
                                )}
                              </div>
                            </div>

                            {p.active_allergies.length > 0 && (
                              <div className="pt-1 flex flex-wrap gap-1.5">
                                {p.active_allergies.map((a, idx) => (
                                  <Badge key={idx} variant="critical">
                                    <AlertTriangle className="w-3 h-3" />
                                    Allergy: {a}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="mt-5 pt-4 border-t border-border-warm flex flex-wrap items-center justify-between gap-2">
                          <span className="text-[11px] font-mono tabular-nums text-ink-muted">
                            Last Visit: {p.last_visit_date ? p.last_visit_date.slice(0, 10) : 'None'}
                          </span>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => openPatientDetail(p.id, 'timeline')}
                            >
                              Open Medical Records
                            </Button>
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => openPatientDetail(p.id, 'ai_summary')}
                            >
                              <Sparkles className="w-3.5 h-3.5" />
                              AI Summary
                            </Button>
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>

                  {/* Pagination Controls */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between pt-2">
                      <span className="text-xs text-ink-secondary font-mono tabular-nums">
                        Page {currentPage} of {totalPages} ({sortedPatients.length} patients)
                      </span>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          disabled={currentPage <= 1}
                          onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                        >
                          <ChevronLeft className="w-3.5 h-3.5" />
                          Previous
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          disabled={currentPage >= totalPages}
                          onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                        >
                          Next
                          <ChevronRight className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* ================================================================
              VIEW 3: PATIENT PROFILE, TIMELINE, AI SUMMARY & NEW VISIT
          ================================================================ */}
          {activeNav === 'patient_detail' && selectedPatient && (
            <div className="max-w-7xl mx-auto space-y-6">
              <Card className="p-6">
                <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                  <div>
                    <div className="flex flex-wrap items-center gap-2.5">
                      <h1 className="font-serif text-2xl sm:text-3xl font-semibold tracking-[-0.02em] text-ink-primary">
                        {selectedPatient.first_name} {selectedPatient.last_name}
                      </h1>
                      <Badge variant="brand" className="font-mono tabular-nums">
                        {selectedPatient.mrn}
                      </Badge>
                      <Badge variant="neutral" className="tabular-nums">
                        DOB: {selectedPatient.date_of_birth} &middot; {selectedPatient.sex}
                      </Badge>
                      <Badge variant="ivory">
                        Blood: {selectedPatient.blood_group || 'Unrecorded'}
                      </Badge>
                    </div>
                    <div className="mt-2.5 text-xs text-ink-secondary flex flex-wrap gap-x-4 gap-y-1 tabular-nums">
                      <span>Phone: {selectedPatient.phone}</span>
                      {selectedPatient.email && <span>Email: {selectedPatient.email}</span>}
                      {selectedPatient.address && <span>Address: {selectedPatient.address}</span>}
                      <span>
                        Emergency: {selectedPatient.emergency_contact_name || 'N/A'} ({selectedPatient.emergency_contact_phone || 'Phone missing'})
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    <Button variant="secondary" size="sm" onClick={openEditPatientModal}>
                      <Edit3 className="w-3.5 h-3.5" />
                      Edit Profile
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => setShowAllergyModal(true)}>
                      <Plus className="w-3.5 h-3.5" />
                      Add Allergy
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => setShowHistoryModal(true)}>
                      <Plus className="w-3.5 h-3.5" />
                      Add History
                    </Button>
                  </div>
                </div>

                {/* Allergy & Baseline History Strip */}
                <div className="mt-4 pt-4 border-t border-border-warm flex flex-wrap items-center gap-2">
                  {selectedPatient.allergies.length > 0 ? (
                    selectedPatient.allergies.map((alg) => (
                      <Badge key={alg.id} variant="critical">
                        <AlertTriangle className="w-3 h-3" />
                        Allergy: {alg.allergen} ({alg.severity}) - {alg.reaction}
                      </Badge>
                    ))
                  ) : (
                    <Badge variant="stable">No Known Drug Allergies</Badge>
                  )}

                  {selectedPatient.medical_history.map((hx) => (
                    <Badge key={hx.id} variant="neutral">
                      <strong>{hx.category}:</strong> {hx.condition_name} ({hx.status})
                    </Badge>
                  ))}
                </div>

                {/* Sub-Navigation Tabs */}
                <div
                  role="tablist"
                  aria-label="Patient record sections"
                  className="mt-5 pt-4 border-t border-border-warm flex flex-wrap items-center gap-2"
                >
                  <button
                    type="button"
                    role="tab"
                    aria-selected={patientSubTab === 'timeline'}
                    onClick={() => setPatientSubTab('timeline')}
                    className={`px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-colors ${
                      patientSubTab === 'timeline'
                        ? 'bg-[#380F17] text-[#EFDFC5]'
                        : 'bg-surface-muted text-ink-primary hover:bg-border-warm/60'
                    }`}
                  >
                    <Clock className="w-3.5 h-3.5" />
                    Clinical Timeline ({selectedPatient.visits.length})
                  </button>

                  <button
                    type="button"
                    role="tab"
                    aria-selected={patientSubTab === 'ai_summary'}
                    onClick={() => {
                      setPatientSubTab('ai_summary');
                      if (!aiSummary) fetchPatientSummary(selectedPatient.id, false);
                    }}
                    className={`px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-colors ${
                      patientSubTab === 'ai_summary'
                        ? 'bg-[#8F0B13] text-white'
                        : 'bg-surface-ivory text-[#380F17] dark:text-[#EFDFC5] border border-[#D7C19D] dark:border-[#5C443B]'
                    }`}
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    AI Grounded Summary
                  </button>

                  <button
                    type="button"
                    role="tab"
                    aria-selected={patientSubTab === 'ai_ask'}
                    onClick={() => {
                      setPatientSubTab('ai_ask');
                      setQueryPatientScope(selectedPatient.id);
                    }}
                    className={`px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-colors ${
                      patientSubTab === 'ai_ask'
                        ? 'bg-[#8F0B13] text-white'
                        : 'bg-surface-muted text-ink-primary hover:bg-border-warm/60'
                    }`}
                  >
                    <Brain className="w-3.5 h-3.5" />
                    Ask AI About Patient
                  </button>

                  <Button
                    variant={patientSubTab === 'new_visit' ? 'primary' : 'ivory'}
                    size="sm"
                    className="sm:ml-auto"
                    onClick={() => setPatientSubTab('new_visit')}
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Add Visit Record
                  </Button>
                </div>
              </Card>

              {/* SUB-TAB 1: STRUCTURED CLINICAL TIMELINE */}
              {patientSubTab === 'timeline' && (
                <div className="space-y-4">
                  {/* Timeline Filter Bar */}
                  {selectedPatient.visits.length > 0 && (
                    <Card className="p-3.5 flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
                      <div className="relative flex-1">
                        <Search className="w-3.5 h-3.5 text-ink-muted absolute left-3 top-2.5" />
                        <Input
                          id="timeline-search"
                          aria-label="Filter visits by complaint, diagnosis, medication, or note"
                          value={visitSearch}
                          onChange={(e) => setVisitSearch(e.target.value)}
                          placeholder="Filter visits by symptom, diagnosis, medication, or clinical note..."
                          className="pl-9"
                        />
                      </div>
                      <div className="sm:w-44">
                        <Select
                          id="timeline-type-filter"
                          aria-label="Filter by visit type"
                          value={visitTypeFilter}
                          onChange={(e) => setVisitTypeFilter(e.target.value)}
                        >
                          <option value="">All Visit Types</option>
                          <option value="OPD">OPD</option>
                          <option value="Follow-up">Follow-up</option>
                          <option value="Emergency">Emergency</option>
                          <option value="Telehealth">Telehealth</option>
                        </Select>
                      </div>
                    </Card>
                  )}

                  {selectedPatient.visits.length === 0 ? (
                    <EmptyState
                      title="No clinical visits recorded yet"
                      description="Create the first encounter record with symptoms, ICD-10 diagnoses, prescriptions, and SOAP notes."
                      actionLabel="Add First Clinical Visit"
                      onAction={() => setPatientSubTab('new_visit')}
                    />
                  ) : filteredVisits.length === 0 ? (
                    <EmptyState
                      title="No visits match your timeline filter"
                      description="Clear the visit keyword or type filter to display all encounters."
                      actionLabel="Clear Timeline Filters"
                      onAction={() => {
                        setVisitSearch('');
                        setVisitTypeFilter('');
                      }}
                    />
                  ) : (
                    filteredVisits.map((visit) => {
                      const isHighlighted = highlightedVisitId === visit.id;
                      return (
                        <Card
                          key={visit.id}
                          className={`p-6 transition-colors ${
                            isHighlighted ? 'border-[#8F0B13] ring-2 ring-[#8F0B13]/25' : ''
                          }`}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2 pb-4 border-b border-border-warm">
                            <div className="flex flex-wrap items-center gap-2.5">
                              <Badge variant="ivory" className="font-mono tabular-nums font-bold">
                                [V-{visit.id}]
                              </Badge>
                              <span className="text-sm font-bold font-mono tabular-nums text-ink-primary">
                                {visit.visit_date.slice(0, 10)}
                              </span>
                              <Badge variant="neutral">{visit.visit_type}</Badge>
                              <span className="text-xs text-ink-secondary">
                                Attending: <strong className="text-ink-primary">{visit.doctor_name}</strong> ({visit.doctor_specialization})
                              </span>
                            </div>

                            <div className="flex flex-wrap items-center gap-2">
                              <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-mono tabular-nums text-ink-secondary">
                                {visit.vitals_bp && <span className="px-2 py-0.5 rounded bg-surface-muted border border-border-warm">BP: {visit.vitals_bp}</span>}
                                {visit.vitals_hr && <span className="px-2 py-0.5 rounded bg-surface-muted border border-border-warm">HR: {visit.vitals_hr} bpm</span>}
                                {visit.vitals_spo2 && <span className="px-2 py-0.5 rounded bg-surface-muted border border-border-warm">SpO2: {visit.vitals_spo2}%</span>}
                                {visit.vitals_weight_kg && <span className="px-2 py-0.5 rounded bg-surface-muted border border-border-warm">Wt: {visit.vitals_weight_kg} kg</span>}
                              </div>
                              <Button variant="ghost" size="sm" onClick={() => openEditVisitModal(visit)}>
                                <Edit3 className="w-3.5 h-3.5" />
                                Edit
                              </Button>
                            </div>
                          </div>

                          <div className="mt-4 flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
                            <div>
                              <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
                                Chief Complaint
                              </span>
                              <div className="text-sm font-semibold text-ink-primary mt-0.5">{visit.chief_complaint}</div>
                            </div>
                            {visit.treatment_plan && (
                              <div className="text-xs text-ink-secondary sm:text-right max-w-md">
                                <strong className="text-ink-primary">Plan:</strong> {visit.treatment_plan}
                              </div>
                            )}
                          </div>

                          {/* Child Tables Grid */}
                          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="p-3.5 rounded-xl bg-surface-muted/60 border border-border-warm">
                              <div className="text-xs font-bold text-ink-primary mb-2 flex items-center gap-1.5">
                                <Activity className="w-3.5 h-3.5 text-[#8F0B13]" />
                                Symptoms ({visit.symptoms.length})
                              </div>
                              <div className="space-y-1.5">
                                {visit.symptoms.map((s) => (
                                  <div key={s.id} className="text-xs bg-surface p-2.5 rounded-lg border border-border-warm">
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="font-semibold text-ink-primary">{s.name}</span>
                                      <span className="font-mono tabular-nums text-[10px] text-ink-muted">[SYM-{s.id}]</span>
                                    </div>
                                    <div className="text-[11px] text-ink-secondary tabular-nums">
                                      Severity: {s.severity}{s.duration_days ? ` · ${s.duration_days} days` : ''}
                                    </div>
                                    {s.notes && <div className="text-[11px] text-ink-secondary mt-0.5">{s.notes}</div>}
                                  </div>
                                ))}
                              </div>
                            </div>

                            <div className="p-3.5 rounded-xl bg-surface-muted/60 border border-border-warm">
                              <div className="text-xs font-bold text-ink-primary mb-2 flex items-center gap-1.5">
                                <Stethoscope className="w-3.5 h-3.5 text-[#380F17] dark:text-[#EFDFC5]" />
                                Diagnoses ({visit.diagnoses.length})
                              </div>
                              <div className="space-y-1.5">
                                {visit.diagnoses.map((d) => (
                                  <div key={d.id} className="text-xs bg-surface p-2.5 rounded-lg border border-border-warm">
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="font-semibold text-ink-primary">{d.condition_name}</span>
                                      <span className="font-mono tabular-nums text-[10px] text-ink-muted">[DX-{d.id}]</span>
                                    </div>
                                    <div className="flex flex-wrap items-center gap-1.5 mt-1">
                                      {d.icd10_code && <Badge variant="mono">ICD-10: {d.icd10_code}</Badge>}
                                      <Badge
                                        variant={
                                          d.status === 'Ruled-out'
                                            ? 'critical'
                                            : d.status === 'Provisional'
                                            ? 'warning'
                                            : 'stable'
                                        }
                                      >
                                        {d.status}
                                      </Badge>
                                    </div>
                                    {d.notes && <div className="text-[11px] text-ink-secondary mt-1">{d.notes}</div>}
                                  </div>
                                ))}
                              </div>
                            </div>

                            <div className="p-3.5 rounded-xl bg-surface-muted/60 border border-border-warm">
                              <div className="text-xs font-bold text-ink-primary mb-2 flex items-center gap-1.5">
                                <Pill className="w-3.5 h-3.5 text-[#8F0B13]" />
                                Prescriptions ({visit.prescriptions.length})
                              </div>
                              <div className="space-y-1.5">
                                {visit.prescriptions.map((rx) => (
                                  <div key={rx.id} className="text-xs bg-surface p-2.5 rounded-lg border border-border-warm">
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="font-semibold text-ink-primary">
                                        {rx.medication?.name} {rx.medication?.strength}
                                      </span>
                                      <span className="font-mono tabular-nums text-[10px] text-ink-muted">[RX-{rx.id}]</span>
                                    </div>
                                    <div className="text-[11px] text-ink-secondary font-medium tabular-nums">
                                      {rx.dosage} &middot; {rx.frequency} ({rx.duration_days || 'ongoing'}d)
                                    </div>
                                    {rx.instructions && (
                                      <div className="text-[11px] text-ink-muted mt-0.5">{rx.instructions}</div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>

                          <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
                            {visit.clinical_notes.length > 0 && (
                              <div className="p-3.5 rounded-xl bg-surface-muted/60 border border-border-warm">
                                <div className="text-xs font-bold text-ink-primary mb-1.5 flex items-center justify-between">
                                  <span className="flex items-center gap-1.5">
                                    <FileText className="w-3.5 h-3.5 text-ink-secondary" />
                                    Clinical Note ({visit.clinical_notes[0].note_type})
                                  </span>
                                  <span className="font-mono tabular-nums text-[10px] text-ink-muted">
                                    [NOTE-{visit.clinical_notes[0].id}]
                                  </span>
                                </div>
                                <p className="text-xs text-ink-secondary leading-relaxed whitespace-pre-line max-w-prose">
                                  {visit.clinical_notes[0].content}
                                </p>
                              </div>
                            )}

                            {visit.test_results.length > 0 && (
                              <div className="p-3.5 rounded-xl bg-surface-muted/60 border border-border-warm">
                                <div className="text-xs font-bold text-ink-primary mb-1.5 flex items-center gap-1.5">
                                  <Microscope className="w-3.5 h-3.5 text-[#8F0B13]" />
                                  Laboratory &amp; Diagnostic Results ({visit.test_results.length})
                                </div>
                                <div className="space-y-1.5">
                                  {visit.test_results.map((t) => (
                                    <div
                                      key={t.id}
                                      className="text-xs bg-surface p-2.5 rounded-lg border border-border-warm flex items-center justify-between gap-2"
                                    >
                                      <div>
                                        <span className="font-semibold text-ink-primary">{t.test_name}: </span>
                                        <span className="font-mono tabular-nums font-bold text-ink-primary">
                                          {t.value} {t.unit}
                                        </span>
                                        <span className="text-[11px] text-ink-secondary ml-1.5 tabular-nums">
                                          (Ref: {t.reference_range || 'Standard'})
                                        </span>
                                      </div>
                                      <div className="flex items-center gap-1.5 shrink-0">
                                        <Badge variant={t.flag === 'Normal' ? 'stable' : 'critical'}>
                                          {t.flag}
                                        </Badge>
                                        <span className="font-mono tabular-nums text-[10px] text-ink-muted">[LAB-{t.id}]</span>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </Card>
                      );
                    })
                  )}
                </div>
              )}

              {/* SUB-TAB 2: AI-POWERED GROUNDED SUMMARY */}
              {patientSubTab === 'ai_summary' && (
                <div className="space-y-5">
                  {summaryLoading && (
                    <div className="space-y-4">
                      <SkeletonBlock className="h-28" />
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <SkeletonBlock className="h-44" />
                        <SkeletonBlock className="h-44" />
                      </div>
                    </div>
                  )}

                  {!summaryLoading && aiSummary && (
                    <div className="space-y-5">
                      {/* Burgundy AI Clinical Decision Support Banner */}
                      <Card variant="brand" className="p-5">
                        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                          <div className="space-y-1.5">
                            <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-[#EFDFC5]">
                              <Sparkles className="w-4 h-4" />
                              AI-Generated Synthesis &middot; {aiSummary.provider_used}
                            </div>
                            <p className="text-xs text-[#EFDFC5]/85 max-w-3xl leading-relaxed">
                              {aiSummary.disclaimer}
                            </p>
                            <div className="flex flex-wrap gap-2 pt-1 text-[11px] font-mono text-[#EFDFC5]/75 tabular-nums">
                              <span>Indexed Rows: {aiSummary.validation_stats.source_records_indexed}</span>
                              <span>&middot;</span>
                              <span>Cache: {aiSummary.cached ? 'Hit' : 'Freshly Computed'}</span>
                              {flaggedCountForCurrentPatient > 0 && (
                                <>
                                  <span>&middot;</span>
                                  <span className="text-[#FCA5A5] font-semibold">
                                    Flagged for Clinician Review: {flaggedCountForCurrentPatient}
                                  </span>
                                </>
                              )}
                            </div>
                          </div>

                          <div className="flex flex-wrap items-center gap-3 shrink-0">
                            <div className="px-3.5 py-2 rounded-lg bg-[#2A0B11] border border-[#561925] text-xs">
                              <div className="text-[10px] uppercase text-[#EFDFC5]/70 font-mono">Citation Verification</div>
                              <div className="font-bold text-[#EFDFC5] tabular-nums">
                                {aiSummary.validation_stats.verified_citations} / {aiSummary.validation_stats.total_citations_emitted} Verified ({Math.round(aiSummary.validation_stats.grounding_score * 100)}%)
                              </div>
                            </div>
                            <Button
                              variant="ivory"
                              size="sm"
                              onClick={() => fetchPatientSummary(selectedPatient.id, true)}
                            >
                              <RefreshCw className="w-3.5 h-3.5" />
                              Re-Synthesize
                            </Button>
                          </div>
                        </div>
                      </Card>

                      <p className="text-xs text-ink-secondary">
                        Select any citation tag (<code className="font-mono text-[#8F0B13] dark:text-[#EFDFC5] font-semibold">[V-1]</code>, <code className="font-mono text-[#8F0B13] dark:text-[#EFDFC5] font-semibold">[SYM-2]</code>) to inspect the raw database row, or click <strong>Flag Issue</strong> to mark an inaccurate statement.
                      </p>

                      {/* Warm Ivory AI Synthesis Panels */}
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                        {[
                          { key: 'overview', title: 'Executive Clinical Overview', icon: ClipboardList, items: aiSummary.executive_overview, variant: 'ivory' as const },
                          { key: 'symptoms', title: 'Recurring Symptoms & Frequency', icon: Activity, items: aiSummary.recurring_symptoms, variant: 'ivory' as const },
                          { key: 'diagnoses', title: 'Diagnoses & ICD-10 Progression', icon: Stethoscope, items: aiSummary.active_and_past_diagnoses, variant: 'ivory' as const },
                          { key: 'meds', title: 'Medication & Prescription History', icon: Pill, items: aiSummary.medication_history, variant: 'ivory' as const },
                          { key: 'labs', title: 'Laboratory Trends & Abnormal Flags', icon: Microscope, items: aiSummary.abnormal_test_trends, variant: 'ivory' as const },
                        ].map((sec) => {
                          const Icon = sec.icon;
                          return (
                            <Card key={sec.key} variant={sec.variant} className="p-5">
                              <h3 className="text-sm font-bold text-ink-primary mb-3 flex items-center gap-2">
                                <Icon className="w-4 h-4 text-[#8F0B13] dark:text-[#EFDFC5]" />
                                {sec.title}
                              </h3>
                              <ul className="space-y-2.5 text-xs text-ink-primary leading-relaxed">
                                {sec.items.map((stmt, idx) => {
                                  const cKey = `p${selectedPatient.id}:${sec.key}:${idx}`;
                                  return (
                                    <li key={idx} className="p-3 rounded-lg bg-surface border border-border-warm">
                                      <div>
                                        <span>{stmt.text}</span>
                                        {renderCitationBadges(stmt.citations, aiSummary.citation_index)}
                                      </div>
                                      {renderFlagButton(cKey)}
                                    </li>
                                  );
                                })}
                              </ul>
                            </Card>
                          );
                        })}

                        <Card variant="ivory" className="p-5">
                          <h3 className="text-sm font-bold text-ink-primary mb-3 flex items-center gap-2">
                            <ShieldAlert className="w-4 h-4 text-[#DC2011]" />
                            Allergies, Data Gaps &amp; Diagnostic Revisions
                          </h3>
                          <ul className="space-y-2.5 text-xs text-ink-primary leading-relaxed">
                            {aiSummary.allergies_and_alerts.map((stmt, idx) => {
                              const cKey = `p${selectedPatient.id}:alg:${idx}`;
                              return (
                                <li
                                  key={`alg-${idx}`}
                                  className="p-3 rounded-lg bg-[var(--status-critical-bg)] border border-[var(--status-critical-border)] text-[var(--status-critical-fg)] font-medium"
                                >
                                  <div>
                                    <span>{stmt.text}</span>
                                    {renderCitationBadges(stmt.citations, aiSummary.citation_index)}
                                  </div>
                                  {renderFlagButton(cKey)}
                                </li>
                              );
                            })}
                            {aiSummary.data_gaps_and_conflicts.map((stmt, idx) => {
                              const cKey = `p${selectedPatient.id}:gap:${idx}`;
                              return (
                                <li key={`gap-${idx}`} className="p-3 rounded-lg bg-surface border border-border-warm">
                                  <div>
                                    <span>{stmt.text}</span>
                                    {renderCitationBadges(stmt.citations, aiSummary.citation_index)}
                                  </div>
                                  {renderFlagButton(cKey)}
                                </li>
                              );
                            })}
                          </ul>
                        </Card>
                      </div>

                      {/* Chronological Source Table */}
                      <Card className="overflow-hidden">
                        <div className="p-5 border-b border-border-warm">
                          <h3 className="text-sm font-bold text-ink-primary">
                            Chronological Medical History Overview
                          </h3>
                        </div>
                        <div className="overflow-x-auto">
                          <table className="w-full text-left border-collapse text-xs">
                            <thead>
                              <tr className="bg-[#380F17] text-[#EFDFC5] text-[11px] font-semibold uppercase">
                                <th className="py-3 px-4">Date &amp; Tag</th>
                                <th className="py-3 px-4">Chief Complaint</th>
                                <th className="py-3 px-4">Diagnoses</th>
                                <th className="py-3 px-4">Prescriptions</th>
                                <th className="py-3 px-4">Abnormal Labs</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-border-warm">
                              {aiSummary.chronological_timeline.map((ev) => (
                                <tr key={ev.visit_id} className="hover:bg-surface-muted/50">
                                  <td className="py-3 px-4 whitespace-nowrap tabular-nums">
                                    <div className="font-bold text-ink-primary font-mono">{ev.visit_date}</div>
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setHighlightedVisitId(ev.visit_id);
                                        setPatientSubTab('timeline');
                                      }}
                                      className="font-mono text-[11px] text-[#8F0B13] dark:text-[#EFDFC5] underline"
                                    >
                                      [{ev.visit_tag}] ({ev.visit_type})
                                    </button>
                                  </td>
                                  <td className="py-3 px-4 text-ink-primary">{ev.chief_complaint}</td>
                                  <td className="py-3 px-4 text-ink-secondary">{ev.diagnoses.join('; ') || 'None'}</td>
                                  <td className="py-3 px-4 text-ink-secondary">{ev.prescriptions.join('; ') || 'None'}</td>
                                  <td className="py-3 px-4 text-[var(--status-critical-fg)] font-medium">
                                    {ev.abnormal_labs.join('; ') || 'All Normal'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </Card>
                    </div>
                  )}
                </div>
              )}

              {/* SUB-TAB 3: PATIENT-SCOPED NATURAL LANGUAGE Q&A */}
              {patientSubTab === 'ai_ask' && (
                <Card className="p-6 space-y-5">
                  <div>
                    <h3 className="text-base font-bold text-ink-primary">
                      Historical Record Retrieval for {selectedPatient.first_name} {selectedPatient.last_name} ({selectedPatient.mrn})
                    </h3>
                    <p className="text-xs text-ink-secondary mt-0.5">
                      Ask natural-language questions. SQL filters retrieve matching rows alongside citation-locked explanations.
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {PRESET_QUESTIONS.map((q, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => {
                          setNlQuery(q);
                          runNaturalLanguageQuery(q, selectedPatient.id);
                        }}
                        className="text-xs px-3 py-1.5 rounded-lg bg-surface-muted hover:bg-surface-ivory border border-border-warm text-ink-primary transition-colors"
                      >
                        {q}
                      </button>
                    ))}
                  </div>

                  <div className="flex flex-col sm:flex-row gap-2">
                    <Input
                      id="patient-nl-query"
                      aria-label="Ask natural-language question about patient"
                      value={nlQuery}
                      onChange={(e) => setNlQuery(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && runNaturalLanguageQuery(nlQuery, selectedPatient.id)}
                      placeholder="Ask e.g. 'What were this patient's previous diagnoses?'"
                      className="flex-1"
                    />
                    <Button
                      variant="primary"
                      loading={nlLoading}
                      onClick={() => runNaturalLanguageQuery(nlQuery, selectedPatient.id)}
                    >
                      <Sparkles className="w-4 h-4" />
                      {nlLoading ? 'Retrieving...' : 'Retrieve & Answer'}
                    </Button>
                  </div>

                  {nlResult && (
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-3">
                      <div className="lg:col-span-6">
                        <Card variant="ivory" className="p-4 space-y-3">
                          <div className="text-xs font-bold text-ink-primary flex items-center gap-1.5">
                            <Sparkles className="w-4 h-4 text-[#8F0B13]" />
                            AI Grounded Explanation
                          </div>
                          <p className="text-xs text-ink-primary font-medium">{nlResult.direct_summary}</p>
                          <div className="space-y-2">
                            {nlResult.answer_statements.map((stmt, idx) => (
                              <div key={idx} className="p-3 rounded-lg bg-surface border border-border-warm text-xs text-ink-primary">
                                <span>{stmt.text}</span>
                                {renderCitationBadges(stmt.citations, nlResult.citation_index)}
                              </div>
                            ))}
                          </div>
                        </Card>
                      </div>

                      <div className="lg:col-span-6 space-y-2.5">
                        <div className="text-xs font-bold text-ink-secondary uppercase tracking-wider">
                          Supporting Relational Source Records ({nlResult.retrieved_records.length})
                        </div>
                        {nlResult.retrieved_records.length === 0 ? (
                          <EmptyState
                            title="No matching source records found"
                            description="The retriever found zero rows for this query and did not extrapolate missing clinical facts."
                          />
                        ) : (
                          <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                            {nlResult.retrieved_records.map((card) => (
                              <Card key={card.citation_tag} className="p-3 hover:border-[#8F0B13] transition-colors text-xs">
                                <div className="flex items-center justify-between gap-2">
                                  <span className="font-bold text-ink-primary">{card.title}</span>
                                  <Badge variant="ivory" className="font-mono tabular-nums">
                                    [{card.citation_tag}]
                                  </Badge>
                                </div>
                                <div className="text-ink-secondary mt-1">{card.details}</div>
                                <div className="mt-1.5 text-[11px] text-ink-muted flex items-center justify-between">
                                  <span className="tabular-nums">
                                    Date: {card.visit_date || 'Baseline'} &middot; {card.doctor_name || ''}
                                  </span>
                                  {card.visit_id && (
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setHighlightedVisitId(card.visit_id!);
                                        setPatientSubTab('timeline');
                                      }}
                                      className="text-[#8F0B13] dark:text-[#EFDFC5] font-semibold hover:underline"
                                    >
                                      View in Timeline &rarr;
                                    </button>
                                  )}
                                </div>
                              </Card>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </Card>
              )}

              {/* SUB-TAB 4: MULTI-ITEM NEW VISIT & AI CLINICAL NOTE EXTRACTOR */}
              {patientSubTab === 'new_visit' && (
                <form onSubmit={handleCreateVisit}>
                  <Card className="p-6 space-y-6">
                    <div className="pb-4 border-b border-border-warm">
                      <h3 className="text-base font-bold text-ink-primary">
                        Record Clinical Encounter for {selectedPatient.first_name} {selectedPatient.last_name}
                      </h3>
                      <p className="text-xs text-ink-secondary mt-0.5">
                        Paste a consultation note to auto-populate structured items, or enter multiple symptoms, diagnoses, prescriptions, and labs manually.
                      </p>
                    </div>

                    <Card variant="ivory" className="p-4 space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <label htmlFor="visit-note" className="text-xs font-bold text-ink-primary flex items-center gap-1.5">
                          <Sparkles className="w-4 h-4 text-[#8F0B13]" />
                          Clinical Consultation Note (SOAP / Progress Note)
                        </label>
                        <Button
                          variant="brand"
                          size="sm"
                          loading={extractingNote}
                          onClick={handleAutoExtractFromNote}
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          {extractingNote ? 'Extracting...' : 'AI Auto-Extract Entities'}
                        </Button>
                      </div>
                      <Textarea
                        id="visit-note"
                        rows={3}
                        value={visitForm.note_content}
                        onChange={(e) => setVisitForm({ ...visitForm, note_content: e.target.value })}
                        placeholder="Example: Patient presents with severe throbbing headache and photophobia for 3 days. Suspected migraine with aura. Prescribed Sumatriptan 50mg PRN. Follow up in 2 weeks."
                      />
                    </Card>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <Select
                        id="visit-type"
                        label="Visit Type"
                        value={visitForm.visit_type}
                        onChange={(e) => setVisitForm({ ...visitForm, visit_type: e.target.value })}
                      >
                        <option value="OPD">OPD</option>
                        <option value="Follow-up">Follow-up</option>
                        <option value="Emergency">Emergency</option>
                        <option value="Telehealth">Telehealth</option>
                      </Select>
                      <div className="sm:col-span-2">
                        <Input
                          id="visit-cc"
                          label="Chief Complaint"
                          required
                          value={visitForm.chief_complaint}
                          onChange={(e) => setVisitForm({ ...visitForm, chief_complaint: e.target.value })}
                          placeholder="Primary reason for encounter"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <Input
                        id="visit-bp"
                        label="Blood Pressure"
                        value={visitForm.vitals_bp}
                        onChange={(e) => setVisitForm({ ...visitForm, vitals_bp: e.target.value })}
                        className="tabular-nums"
                      />
                      <Input
                        id="visit-hr"
                        label="Heart Rate (20-300 bpm)"
                        type="number"
                        min={20}
                        max={300}
                        value={visitForm.vitals_hr}
                        onChange={(e) => setVisitForm({ ...visitForm, vitals_hr: e.target.value })}
                        className="tabular-nums"
                      />
                      <Input
                        id="visit-spo2"
                        label="SpO2 (50-100%)"
                        type="number"
                        min={50}
                        max={100}
                        value={visitForm.vitals_spo2}
                        onChange={(e) => setVisitForm({ ...visitForm, vitals_spo2: e.target.value })}
                        className="tabular-nums"
                      />
                      <Input
                        id="visit-wt"
                        label="Weight (kg)"
                        value={visitForm.vitals_weight_kg}
                        onChange={(e) => setVisitForm({ ...visitForm, vitals_weight_kg: e.target.value })}
                        className="tabular-nums"
                      />
                    </div>

                    {/* Multi-Row Symptoms */}
                    <div className="p-4 rounded-xl bg-surface-muted/50 border border-border-warm space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-ink-primary">Symptoms ({visitForm.symptoms.length})</span>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() =>
                            setVisitForm((prev) => ({
                              ...prev,
                              symptoms: [...prev.symptoms, { name: '', severity: 'Moderate', duration_days: 3, notes: '' }],
                            }))
                          }
                        >
                          <Plus className="w-3.5 h-3.5" /> Add Symptom
                        </Button>
                      </div>
                      {visitForm.symptoms.map((sym, idx) => (
                        <div key={idx} className="grid grid-cols-1 sm:grid-cols-12 gap-2 items-center">
                          <div className="sm:col-span-6">
                            <Input
                              id={`sym-name-${idx}`}
                              aria-label={`Symptom ${idx + 1} name`}
                              placeholder="Symptom name (e.g. Recurring Headache)"
                              value={sym.name}
                              onChange={(e) => {
                                const next = [...visitForm.symptoms];
                                next[idx].name = e.target.value;
                                setVisitForm({ ...visitForm, symptoms: next });
                              }}
                            />
                          </div>
                          <div className="sm:col-span-3">
                            <Select
                              id={`sym-sev-${idx}`}
                              aria-label={`Symptom ${idx + 1} severity`}
                              value={sym.severity}
                              onChange={(e) => {
                                const next = [...visitForm.symptoms];
                                next[idx].severity = e.target.value;
                                setVisitForm({ ...visitForm, symptoms: next });
                              }}
                            >
                              <option value="Mild">Mild</option>
                              <option value="Moderate">Moderate</option>
                              <option value="Severe">Severe</option>
                            </Select>
                          </div>
                          <div className="sm:col-span-2">
                            <Input
                              id={`sym-dur-${idx}`}
                              type="number"
                              min={1}
                              aria-label={`Symptom ${idx + 1} duration days`}
                              value={sym.duration_days}
                              onChange={(e) => {
                                const next = [...visitForm.symptoms];
                                next[idx].duration_days = Number(e.target.value) || 1;
                                setVisitForm({ ...visitForm, symptoms: next });
                              }}
                            />
                          </div>
                          <div className="sm:col-span-1 flex justify-end">
                            {visitForm.symptoms.length > 1 && (
                              <button
                                type="button"
                                aria-label={`Remove symptom ${idx + 1}`}
                                onClick={() =>
                                  setVisitForm((prev) => ({
                                    ...prev,
                                    symptoms: prev.symptoms.filter((_, i) => i !== idx),
                                  }))
                                }
                                className="p-1.5 rounded-lg text-[#DC2011] hover:bg-[var(--status-critical-bg)]"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Multi-Row Diagnoses */}
                    <div className="p-4 rounded-xl bg-surface-muted/50 border border-border-warm space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-ink-primary">Diagnoses ({visitForm.diagnoses.length})</span>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() =>
                            setVisitForm((prev) => ({
                              ...prev,
                              diagnoses: [...prev.diagnoses, { condition_name: '', icd10_code: '', status: 'Confirmed', notes: '' }],
                            }))
                          }
                        >
                          <Plus className="w-3.5 h-3.5" /> Add Diagnosis
                        </Button>
                      </div>
                      {visitForm.diagnoses.map((dx, idx) => (
                        <div key={idx} className="grid grid-cols-1 sm:grid-cols-12 gap-2 items-center">
                          <div className="sm:col-span-6">
                            <Input
                              id={`dx-name-${idx}`}
                              aria-label={`Diagnosis ${idx + 1} condition`}
                              placeholder="Condition name (e.g. Migraine with Aura)"
                              value={dx.condition_name}
                              onChange={(e) => {
                                const next = [...visitForm.diagnoses];
                                next[idx].condition_name = e.target.value;
                                setVisitForm({ ...visitForm, diagnoses: next });
                              }}
                            />
                          </div>
                          <div className="sm:col-span-2">
                            <Input
                              id={`dx-icd-${idx}`}
                              aria-label={`Diagnosis ${idx + 1} ICD-10 code`}
                              placeholder="ICD-10"
                              className="font-mono"
                              value={dx.icd10_code}
                              onChange={(e) => {
                                const next = [...visitForm.diagnoses];
                                next[idx].icd10_code = e.target.value;
                                setVisitForm({ ...visitForm, diagnoses: next });
                              }}
                            />
                          </div>
                          <div className="sm:col-span-3">
                            <Select
                              id={`dx-status-${idx}`}
                              aria-label={`Diagnosis ${idx + 1} status`}
                              value={dx.status}
                              onChange={(e) => {
                                const next = [...visitForm.diagnoses];
                                next[idx].status = e.target.value;
                                setVisitForm({ ...visitForm, diagnoses: next });
                              }}
                            >
                              <option value="Confirmed">Confirmed</option>
                              <option value="Provisional">Provisional</option>
                              <option value="Controlled">Controlled</option>
                              <option value="Ruled-out">Ruled-out</option>
                              <option value="Resolved">Resolved</option>
                            </Select>
                          </div>
                          <div className="sm:col-span-1 flex justify-end">
                            {visitForm.diagnoses.length > 1 && (
                              <button
                                type="button"
                                aria-label={`Remove diagnosis ${idx + 1}`}
                                onClick={() =>
                                  setVisitForm((prev) => ({
                                    ...prev,
                                    diagnoses: prev.diagnoses.filter((_, i) => i !== idx),
                                  }))
                                }
                                className="p-1.5 rounded-lg text-[#DC2011] hover:bg-[var(--status-critical-bg)]"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Multi-Row Prescriptions */}
                    <div className="p-4 rounded-xl bg-surface-muted/50 border border-border-warm space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-ink-primary">Prescriptions ({visitForm.prescriptions.length})</span>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() =>
                            setVisitForm((prev) => ({
                              ...prev,
                              prescriptions: [
                                ...prev.prescriptions,
                                { medication_name: '', strength: '50mg', dosage: '1 tablet', frequency: 'Once daily (OD)', duration_days: 14, instructions: '' },
                              ],
                            }))
                          }
                        >
                          <Plus className="w-3.5 h-3.5" /> Add Prescription
                        </Button>
                      </div>
                      <datalist id="med-options">
                        {medCatalog.map((m) => (
                          <option key={m.id} value={m.name}>
                            {m.generic_name} ({m.strength})
                          </option>
                        ))}
                      </datalist>
                      {visitForm.prescriptions.map((rx, idx) => (
                        <div key={idx} className="grid grid-cols-1 sm:grid-cols-12 gap-2 items-center">
                          <div className="sm:col-span-4">
                            <Input
                              id={`rx-name-${idx}`}
                              list="med-options"
                              aria-label={`Prescription ${idx + 1} medication`}
                              placeholder="Medication (e.g. Sumatriptan)"
                              value={rx.medication_name}
                              onChange={(e) => {
                                const next = [...visitForm.prescriptions];
                                next[idx].medication_name = e.target.value;
                                setVisitForm({ ...visitForm, prescriptions: next });
                              }}
                            />
                          </div>
                          <div className="sm:col-span-3">
                            <Input
                              id={`rx-dose-${idx}`}
                              aria-label={`Prescription ${idx + 1} dosage`}
                              placeholder="Dosage"
                              value={rx.dosage}
                              onChange={(e) => {
                                const next = [...visitForm.prescriptions];
                                next[idx].dosage = e.target.value;
                                setVisitForm({ ...visitForm, prescriptions: next });
                              }}
                            />
                          </div>
                          <div className="sm:col-span-4">
                            <Input
                              id={`rx-freq-${idx}`}
                              aria-label={`Prescription ${idx + 1} frequency`}
                              placeholder="Frequency"
                              value={rx.frequency}
                              onChange={(e) => {
                                const next = [...visitForm.prescriptions];
                                next[idx].frequency = e.target.value;
                                setVisitForm({ ...visitForm, prescriptions: next });
                              }}
                            />
                          </div>
                          <div className="sm:col-span-1 flex justify-end">
                            {visitForm.prescriptions.length > 1 && (
                              <button
                                type="button"
                                aria-label={`Remove prescription ${idx + 1}`}
                                onClick={() =>
                                  setVisitForm((prev) => ({
                                    ...prev,
                                    prescriptions: prev.prescriptions.filter((_, i) => i !== idx),
                                  }))
                                }
                                className="p-1.5 rounded-lg text-[#DC2011] hover:bg-[var(--status-critical-bg)]"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Multi-Row Laboratory Tests */}
                    <div className="p-4 rounded-xl bg-surface-muted/50 border border-border-warm space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-ink-primary">Laboratory &amp; Diagnostic Results ({visitForm.test_results.length})</span>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() =>
                            setVisitForm((prev) => ({
                              ...prev,
                              test_results: [
                                ...prev.test_results,
                                { test_name: '', value: '', unit: '', reference_range: '', flag: 'Normal', result_date: new Date().toISOString().slice(0, 10) },
                              ],
                            }))
                          }
                        >
                          <Plus className="w-3.5 h-3.5" /> Add Lab Result
                        </Button>
                      </div>
                      {visitForm.test_results.map((lab, idx) => (
                        <div key={idx} className="grid grid-cols-1 sm:grid-cols-12 gap-2 items-center">
                          <div className="sm:col-span-4">
                            <Input
                              id={`lab-name-${idx}`}
                              aria-label={`Lab ${idx + 1} test name`}
                              placeholder="Test name (e.g. HbA1c)"
                              value={lab.test_name}
                              onChange={(e) => {
                                const next = [...visitForm.test_results];
                                next[idx].test_name = e.target.value;
                                setVisitForm({ ...visitForm, test_results: next });
                              }}
                            />
                          </div>
                          <div className="sm:col-span-2">
                            <Input
                              id={`lab-val-${idx}`}
                              aria-label={`Lab ${idx + 1} value`}
                              placeholder="Value"
                              value={lab.value}
                              onChange={(e) => {
                                const next = [...visitForm.test_results];
                                next[idx].value = e.target.value;
                                setVisitForm({ ...visitForm, test_results: next });
                              }}
                            />
                          </div>
                          <div className="sm:col-span-2">
                            <Input
                              id={`lab-unit-${idx}`}
                              aria-label={`Lab ${idx + 1} unit`}
                              placeholder="Unit"
                              value={lab.unit}
                              onChange={(e) => {
                                const next = [...visitForm.test_results];
                                next[idx].unit = e.target.value;
                                setVisitForm({ ...visitForm, test_results: next });
                              }}
                            />
                          </div>
                          <div className="sm:col-span-3">
                            <Select
                              id={`lab-flag-${idx}`}
                              aria-label={`Lab ${idx + 1} flag`}
                              value={lab.flag}
                              onChange={(e) => {
                                const next = [...visitForm.test_results];
                                next[idx].flag = e.target.value;
                                setVisitForm({ ...visitForm, test_results: next });
                              }}
                            >
                              <option value="Normal">Normal</option>
                              <option value="High">High</option>
                              <option value="Low">Low</option>
                              <option value="Critical">Critical</option>
                              <option value="Abnormal">Abnormal</option>
                            </Select>
                          </div>
                          <div className="sm:col-span-1 flex justify-end">
                            {visitForm.test_results.length > 1 && (
                              <button
                                type="button"
                                aria-label={`Remove lab ${idx + 1}`}
                                onClick={() =>
                                  setVisitForm((prev) => ({
                                    ...prev,
                                    test_results: prev.test_results.filter((_, i) => i !== idx),
                                  }))
                                }
                                className="p-1.5 rounded-lg text-[#DC2011] hover:bg-[var(--status-critical-bg)]"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    <Textarea
                      id="visit-plan"
                      label="Treatment Plan & Follow-Up"
                      rows={3}
                      value={visitForm.treatment_plan}
                      onChange={(e) => setVisitForm({ ...visitForm, treatment_plan: e.target.value })}
                      placeholder="Document management plan and follow-up interval..."
                    />

                    <div className="flex justify-end gap-3">
                      <Button variant="secondary" onClick={() => setPatientSubTab('timeline')}>
                        Cancel
                      </Button>
                      <Button type="submit" variant="primary" loading={submittingVisit}>
                        {submittingVisit ? 'Saving Encounter...' : 'Save Encounter Record'}
                      </Button>
                    </div>
                  </Card>
                </form>
              )}
            </div>
          )}

          {/* ================================================================
              VIEW 4: GLOBAL AI NATURAL-LANGUAGE HISTORICAL RETRIEVAL
          ================================================================ */}
          {activeNav === 'ai_retrieval' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div>
                <h1 className="font-serif text-2xl sm:text-3xl font-semibold tracking-[-0.02em] text-ink-primary flex items-center gap-2.5">
                  <Sparkles className="w-6 h-6 text-[#8F0B13]" />
                  Intelligent Historical Record Retrieval
                </h1>
                <p className="text-xs sm:text-sm text-ink-secondary mt-1">
                  Query one patient or the entire database in plain English. SQL filters and clinical synonym expansion retrieve matching relational rows alongside grounded answers.
                </p>
              </div>

              <Card className="p-6 space-y-4">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
                  <div className="lg:col-span-4">
                    <Select
                      id="query-scope"
                      label="Patient Scope"
                      value={queryPatientScope}
                      onChange={(e) =>
                        setQueryPatientScope(e.target.value === 'all' ? 'all' : Number(e.target.value))
                      }
                    >
                      <option value="all">All Authorised Patients (Cohort Search)</option>
                      {patients.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.first_name} {p.last_name} ({p.mrn})
                        </option>
                      ))}
                    </Select>
                  </div>

                  <div className="lg:col-span-8">
                    <label htmlFor="nl-query-input" className="block text-xs font-semibold text-ink-primary mb-1">
                      Clinical Question
                    </label>
                    <div className="flex gap-2">
                      <Input
                        id="nl-query-input"
                        value={nlQuery}
                        onChange={(e) => setNlQuery(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && runNaturalLanguageQuery()}
                        placeholder="e.g. Find previous records mentioning recurring headaches..."
                        className="flex-1"
                      />
                      <Button
                        variant="primary"
                        loading={nlLoading}
                        onClick={() => runNaturalLanguageQuery()}
                      >
                        <Search className="w-4 h-4" />
                        {nlLoading ? 'Searching...' : 'Run Query'}
                      </Button>
                    </div>
                  </div>
                </div>

                <div>
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted block mb-2">
                    Sample Evaluation Queries
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {PRESET_QUESTIONS.map((q, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => {
                          setNlQuery(q);
                          runNaturalLanguageQuery(q, queryPatientScope);
                        }}
                        className="text-xs px-3 py-1.5 rounded-lg bg-surface-muted hover:bg-surface-ivory border border-border-warm text-ink-primary transition-colors"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              </Card>

              {nlResult && (
                <div className="space-y-6">
                  <Card variant="brand" className="p-4 flex flex-wrap items-center justify-between gap-3 text-xs">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[#EFDFC5] font-mono font-semibold flex items-center gap-1">
                        <Filter className="w-3.5 h-3.5" /> SQL Query Planner:
                      </span>
                      <span className="px-2.5 py-1 rounded bg-[#2A0B11] font-mono text-[#EFDFC5]">
                        Tables: {nlResult.interpreted_filters.target_record_types.join(', ')}
                      </span>
                      {nlResult.interpreted_filters.date_from && (
                        <span className="px-2.5 py-1 rounded bg-[#2A0B11] font-mono tabular-nums text-[#EFDFC5]">
                          Date &gt;= {nlResult.interpreted_filters.date_from}
                        </span>
                      )}
                      {nlResult.interpreted_filters.expanded_clinical_terms.length > 0 && (
                        <span className="px-2.5 py-1 rounded bg-[#2A0B11] font-mono text-[#EFDFC5]">
                          Terms: {nlResult.interpreted_filters.expanded_clinical_terms.slice(0, 6).join(', ')}
                        </span>
                      )}
                    </div>
                    <span className="font-mono tabular-nums text-[#EFDFC5] font-semibold">
                      Total Matches: {nlResult.total_matches}
                    </span>
                  </Card>

                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    <div className="lg:col-span-5">
                      <Card variant="ivory" className="p-6 space-y-4">
                        <div className="flex items-center justify-between border-b border-border-warm pb-3">
                          <h3 className="text-sm font-bold text-ink-primary flex items-center gap-2">
                            <Sparkles className="w-4 h-4 text-[#8F0B13]" />
                            AI Grounded Synthesis
                          </h3>
                          <Badge variant="brand">Citation-Locked</Badge>
                        </div>
                        <p className="text-xs font-semibold text-ink-primary">{nlResult.direct_summary}</p>
                        <div className="space-y-2.5">
                          {nlResult.answer_statements.map((stmt, idx) => (
                            <div
                              key={idx}
                              className="p-3 rounded-lg bg-surface border border-border-warm text-xs text-ink-primary leading-relaxed"
                            >
                              <span>{stmt.text}</span>
                              {renderCitationBadges(stmt.citations, nlResult.citation_index)}
                            </div>
                          ))}
                        </div>
                        <div className="pt-3 border-t border-border-warm text-[11px] text-ink-secondary">
                          {nlResult.disclaimer}
                        </div>
                      </Card>
                    </div>

                    <div className="lg:col-span-7">
                      <Card className="p-6 space-y-4">
                        <div className="flex items-center justify-between border-b border-border-warm pb-3">
                          <h3 className="text-sm font-bold text-ink-primary flex items-center gap-2">
                            <Database className="w-4 h-4 text-[#380F17] dark:text-[#EFDFC5]" />
                            Retrieved Database Records ({nlResult.retrieved_records.length})
                          </h3>
                        </div>

                        {nlResult.retrieved_records.length === 0 ? (
                          <EmptyState
                            title="Zero matching clinical records found"
                            description="The retriever found no records matching those terms and refused to extrapolate unrecorded medical claims."
                          />
                        ) : (
                          <div className="space-y-3">
                            {nlResult.retrieved_records.map((rec) => (
                              <div
                                key={rec.citation_tag}
                                className="p-4 rounded-xl border border-border-warm hover:border-[#8F0B13] bg-surface-muted/40 transition-colors text-xs"
                              >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <div className="flex items-center gap-2">
                                    <Badge variant="crimson" className="font-mono tabular-nums font-bold">
                                      [{rec.citation_tag}]
                                    </Badge>
                                    <span className="font-bold text-ink-primary text-sm">{rec.title}</span>
                                  </div>
                                  <Badge variant="mono">
                                    {rec.patient_name} ({rec.patient_mrn})
                                  </Badge>
                                </div>

                                <p className="mt-2 text-ink-secondary leading-relaxed">{rec.details}</p>

                                <div className="mt-3 pt-2 border-t border-border-warm flex flex-wrap items-center justify-between gap-2 text-[11px] text-ink-muted">
                                  <div className="tabular-nums">
                                    Table: <strong className="text-ink-primary">{rec.record_type}</strong> &middot; Date:{' '}
                                    <strong className="text-ink-primary">{rec.visit_date || 'Patient Profile'}</strong>
                                    {rec.matched_terms.length > 0 && (
                                      <span className="ml-2 text-[#8F0B13] dark:text-[#EFDFC5]">
                                        Matched: {rec.matched_terms.join(', ')}
                                      </span>
                                    )}
                                  </div>
                                  <button
                                    type="button"
                                    onClick={() => openPatientDetail(rec.patient_id, 'timeline', rec.visit_id || null)}
                                    className="text-[#8F0B13] dark:text-[#EFDFC5] font-semibold hover:underline"
                                  >
                                    Open Source Timeline &rarr;
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </Card>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ================================================================
              VIEW 5: RBAC & SECURITY AUDIT LOGS
          ================================================================ */}
          {activeNav === 'audit' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h1 className="font-serif text-2xl sm:text-3xl font-semibold tracking-[-0.02em] text-ink-primary">
                    Access Control &amp; Clinical Audit Trail
                  </h1>
                  <p className="text-xs sm:text-sm text-ink-secondary mt-0.5">
                    Authentication, patient modifications, AI synthesis, and retrieval queries logged with user role and UTC timestamp.
                  </p>
                </div>
                <div className="sm:w-72">
                  <Input
                    id="audit-filter"
                    aria-label="Filter audit logs"
                    value={auditFilter}
                    onChange={(e) => setAuditFilter(e.target.value)}
                    placeholder="Filter by action, user, or role..."
                  />
                </div>
              </div>

              <Card className="overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-[#380F17] text-[#EFDFC5] text-[11px] font-semibold uppercase">
                        <th className="py-3 px-4">Timestamp (UTC)</th>
                        <th className="py-3 px-4">Authenticated User</th>
                        <th className="py-3 px-4">Role</th>
                        <th className="py-3 px-4">Action</th>
                        <th className="py-3 px-4">Clinical Audit Detail</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-warm">
                      {filteredAuditLogs.map((log) => (
                        <tr key={log.id} className="hover:bg-surface-muted/40">
                          <td className="py-3 px-4 font-mono tabular-nums text-ink-secondary whitespace-nowrap">
                            {log.created_at.slice(0, 19).replace('T', ' ')}
                          </td>
                          <td className="py-3 px-4 font-semibold text-ink-primary">{log.user_name}</td>
                          <td className="py-3 px-4">
                            <Badge variant={log.user_role === 'admin' ? 'brand' : 'crimson'}>
                              {log.user_role}
                            </Badge>
                          </td>
                          <td className="py-3 px-4 font-mono font-semibold text-[#8F0B13] dark:text-[#EFDFC5]">
                            {log.action}
                          </td>
                          <td className="py-3 px-4 text-ink-secondary">{log.detail}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}
        </main>
      </div>

      {/* ====================================================================
          CITATION SOURCE RECORD INSPECTOR DRAWER
      ==================================================================== */}
      {inspectedCitation && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Citation source record inspector"
          className="fixed inset-y-0 right-0 w-96 max-w-full bg-surface border-l border-border-warm shadow-2xl z-50 p-6 flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-border-warm">
              <div className="flex items-center gap-2">
                <Badge variant="brand" className="font-mono tabular-nums font-bold">
                  [{inspectedCitation.tag}]
                </Badge>
                <span className="text-sm font-bold text-ink-primary">Source Record Inspector</span>
              </div>
              <button
                type="button"
                aria-label="Close source record inspector"
                onClick={() => setInspectedCitation(null)}
                className="p-1.5 rounded-lg text-ink-secondary hover:text-ink-primary hover:bg-surface-muted"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="mt-5 space-y-4 text-xs">
              <Card variant="ivory" className="p-3.5">
                <div className="font-bold text-ink-primary flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-[#8F0B13]" />
                  Verified Relational Database Fact
                </div>
                <p className="mt-1 text-[11px] text-ink-secondary">
                  Maps directly to primary key ID #{inspectedCitation.record_id} in the{' '}
                  <code className="font-mono font-bold text-ink-primary">{inspectedCitation.record_type}</code> table.
                </p>
              </Card>

              <div>
                <div className="text-[11px] font-semibold uppercase text-ink-muted">Record Label</div>
                <div className="text-sm font-bold text-ink-primary mt-0.5">{inspectedCitation.label}</div>
              </div>

              {inspectedCitation.visit_date && (
                <div>
                  <div className="text-[11px] font-semibold uppercase text-ink-muted">Encounter Date</div>
                  <div className="text-xs font-mono tabular-nums text-ink-primary mt-0.5">
                    {inspectedCitation.visit_date}
                  </div>
                </div>
              )}

              <div>
                <div className="text-[11px] font-semibold uppercase text-ink-muted">Stored Relational Content</div>
                <div className="mt-1 p-3.5 rounded-xl bg-surface-muted border border-border-warm text-ink-primary leading-relaxed">
                  {inspectedCitation.snippet}
                </div>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-border-warm space-y-2">
            {inspectedCitation.visit_id && (
              <Button
                variant="primary"
                className="w-full"
                onClick={() => {
                  setHighlightedVisitId(inspectedCitation.visit_id!);
                  setPatientSubTab('timeline');
                  setInspectedCitation(null);
                }}
              >
                Jump to Visit [V-{inspectedCitation.visit_id}] in Timeline
              </Button>
            )}
            <Button variant="secondary" className="w-full" onClick={() => setInspectedCitation(null)}>
              Close Inspector (Esc)
            </Button>
          </div>
        </div>
      )}

      {/* ====================================================================
          MODALS: REGISTER PATIENT, EDIT PATIENT, ADD ALLERGY, ADD HISTORY, EDIT VISIT
      ==================================================================== */}
      <Modal
        open={showNewPatientModal}
        onClose={() => setShowNewPatientModal(false)}
        title="Register New Patient Profile"
        subtitle="Creates a synthetic patient record with a unique server-assigned MRN."
      >
        <form id="new-patient-form" onSubmit={handleCreatePatient} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              id="pat-first"
              label="First Name"
              required
              value={newPat.first_name}
              onChange={(e) => setNewPat({ ...newPat, first_name: e.target.value })}
            />
            <Input
              id="pat-last"
              label="Last Name"
              required
              value={newPat.last_name}
              onChange={(e) => setNewPat({ ...newPat, last_name: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Input
              id="pat-dob"
              label="Date of Birth"
              type="date"
              required
              value={newPat.date_of_birth}
              onChange={(e) => setNewPat({ ...newPat, date_of_birth: e.target.value })}
            />
            <Select
              id="pat-sex"
              label="Sex"
              value={newPat.sex}
              onChange={(e) => setNewPat({ ...newPat, sex: e.target.value })}
            >
              <option value="Male">Male</option>
              <option value="Female">Female</option>
              <option value="Other">Other</option>
            </Select>
            <Input
              id="pat-bg"
              label="Blood Group"
              placeholder="O+, A+, B+..."
              value={newPat.blood_group}
              onChange={(e) => setNewPat({ ...newPat, blood_group: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              id="pat-phone"
              label="Phone Number"
              required
              value={newPat.phone}
              onChange={(e) => setNewPat({ ...newPat, phone: e.target.value })}
            />
            <Input
              id="pat-email"
              label="Email"
              type="email"
              value={newPat.email}
              onChange={(e) => setNewPat({ ...newPat, email: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              id="pat-alg"
              label="Known Allergy (Optional)"
              placeholder="e.g. Penicillin, Sulfa"
              value={newPat.allergy_allergen}
              onChange={(e) => setNewPat({ ...newPat, allergy_allergen: e.target.value })}
            />
            <Input
              id="pat-hx"
              label="Chronic Condition (Optional)"
              placeholder="e.g. Hypertension, Asthma"
              value={newPat.history_condition}
              onChange={(e) => setNewPat({ ...newPat, history_condition: e.target.value })}
            />
          </div>
          <div className="flex justify-end gap-2 pt-3 border-t border-border-warm">
            <Button variant="secondary" onClick={() => setShowNewPatientModal(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={submittingPatient}>
              Generate MRN &amp; Register
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={showEditPatientModal}
        onClose={() => setShowEditPatientModal(false)}
        title="Edit Patient Demographics"
        subtitle={selectedPatient ? `Updating profile for ${selectedPatient.mrn}` : undefined}
      >
        <form onSubmit={handleUpdatePatient} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              id="edit-first"
              label="First Name"
              required
              value={editPat.first_name}
              onChange={(e) => setEditPat({ ...editPat, first_name: e.target.value })}
            />
            <Input
              id="edit-last"
              label="Last Name"
              required
              value={editPat.last_name}
              onChange={(e) => setEditPat({ ...editPat, last_name: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Input
              id="edit-dob"
              label="Date of Birth"
              type="date"
              required
              value={editPat.date_of_birth}
              onChange={(e) => setEditPat({ ...editPat, date_of_birth: e.target.value })}
            />
            <Select
              id="edit-sex"
              label="Sex"
              value={editPat.sex}
              onChange={(e) => setEditPat({ ...editPat, sex: e.target.value })}
            >
              <option value="Male">Male</option>
              <option value="Female">Female</option>
              <option value="Other">Other</option>
            </Select>
            <Input
              id="edit-bg"
              label="Blood Group"
              value={editPat.blood_group}
              onChange={(e) => setEditPat({ ...editPat, blood_group: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              id="edit-phone"
              label="Phone Number"
              required
              value={editPat.phone}
              onChange={(e) => setEditPat({ ...editPat, phone: e.target.value })}
            />
            <Input
              id="edit-email"
              label="Email"
              type="email"
              value={editPat.email}
              onChange={(e) => setEditPat({ ...editPat, email: e.target.value })}
            />
          </div>
          <Input
            id="edit-address"
            label="Address"
            value={editPat.address}
            onChange={(e) => setEditPat({ ...editPat, address: e.target.value })}
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              id="edit-ec-name"
              label="Emergency Contact Name"
              value={editPat.emergency_contact_name}
              onChange={(e) => setEditPat({ ...editPat, emergency_contact_name: e.target.value })}
            />
            <Input
              id="edit-ec-phone"
              label="Emergency Contact Phone"
              value={editPat.emergency_contact_phone}
              onChange={(e) => setEditPat({ ...editPat, emergency_contact_phone: e.target.value })}
            />
          </div>
          <div className="flex justify-end gap-2 pt-3 border-t border-border-warm">
            <Button variant="secondary" onClick={() => setShowEditPatientModal(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={submittingPatient}>
              Save Profile Changes
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={showAllergyModal}
        onClose={() => setShowAllergyModal(false)}
        title="Add Patient Allergy Alert"
        maxWidth="max-w-md"
      >
        <form onSubmit={handleAddAllergy} className="space-y-4">
          <Input
            id="alg-allergen"
            label="Allergen"
            required
            placeholder="e.g. Penicillin, Latex, NSAIDs"
            value={newAllergy.allergen}
            onChange={(e) => setNewAllergy({ ...newAllergy, allergen: e.target.value })}
          />
          <Input
            id="alg-reaction"
            label="Clinical Reaction"
            required
            placeholder="e.g. Urticaria, Bronchospasm"
            value={newAllergy.reaction}
            onChange={(e) => setNewAllergy({ ...newAllergy, reaction: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-3">
            <Select
              id="alg-severity"
              label="Severity"
              value={newAllergy.severity}
              onChange={(e) => setNewAllergy({ ...newAllergy, severity: e.target.value })}
            >
              <option value="Mild">Mild</option>
              <option value="Moderate">Moderate</option>
              <option value="Severe">Severe</option>
              <option value="Life-Threatening">Life-Threatening</option>
            </Select>
            <Select
              id="alg-status"
              label="Status"
              value={newAllergy.status}
              onChange={(e) => setNewAllergy({ ...newAllergy, status: e.target.value })}
            >
              <option value="Active">Active</option>
              <option value="Resolved">Resolved</option>
            </Select>
          </div>
          <div className="flex justify-end gap-2 pt-3 border-t border-border-warm">
            <Button variant="secondary" onClick={() => setShowAllergyModal(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="danger">
              Record Allergy Alert
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={showHistoryModal}
        onClose={() => setShowHistoryModal(false)}
        title="Add Baseline Medical History"
        maxWidth="max-w-md"
      >
        <form onSubmit={handleAddHistory} className="space-y-4">
          <Input
            id="hx-condition"
            label="Condition or Procedure"
            required
            placeholder="e.g. Type 2 Diabetes Mellitus, Appendectomy"
            value={newHistory.condition_name}
            onChange={(e) => setNewHistory({ ...newHistory, condition_name: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-3">
            <Select
              id="hx-category"
              label="Category"
              value={newHistory.category}
              onChange={(e) => setNewHistory({ ...newHistory, category: e.target.value })}
            >
              <option value="Chronic">Chronic</option>
              <option value="Past Illness">Past Illness</option>
              <option value="Surgical">Surgical</option>
              <option value="Family">Family</option>
            </Select>
            <Select
              id="hx-status"
              label="Status"
              value={newHistory.status}
              onChange={(e) => setNewHistory({ ...newHistory, status: e.target.value })}
            >
              <option value="Active">Active</option>
              <option value="Controlled">Controlled</option>
              <option value="Resolved">Resolved</option>
              <option value="Historical">Historical</option>
            </Select>
          </div>
          <Input
            id="hx-onset"
            label="Onset Date (Optional)"
            type="date"
            value={newHistory.onset_date}
            onChange={(e) => setNewHistory({ ...newHistory, onset_date: e.target.value })}
          />
          <Textarea
            id="hx-notes"
            label="Clinical Notes (Optional)"
            rows={2}
            value={newHistory.notes}
            onChange={(e) => setNewHistory({ ...newHistory, notes: e.target.value })}
          />
          <div className="flex justify-end gap-2 pt-3 border-t border-border-warm">
            <Button variant="secondary" onClick={() => setShowHistoryModal(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Save History Item
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={Boolean(editingVisit)}
        onClose={() => setEditingVisit(null)}
        title={editingVisit ? `Edit Visit [V-${editingVisit.id}]` : 'Edit Visit'}
      >
        <form onSubmit={handleUpdateVisit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Select
              id="edit-visit-type"
              label="Visit Type"
              value={editVisitForm.visit_type}
              onChange={(e) => setEditVisitForm({ ...editVisitForm, visit_type: e.target.value })}
            >
              <option value="OPD">OPD</option>
              <option value="Follow-up">Follow-up</option>
              <option value="Emergency">Emergency</option>
              <option value="Telehealth">Telehealth</option>
            </Select>
            <div className="sm:col-span-2">
              <Input
                id="edit-visit-cc"
                label="Chief Complaint"
                required
                value={editVisitForm.chief_complaint}
                onChange={(e) => setEditVisitForm({ ...editVisitForm, chief_complaint: e.target.value })}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Input
              id="edit-visit-bp"
              label="Blood Pressure"
              value={editVisitForm.vitals_bp}
              onChange={(e) => setEditVisitForm({ ...editVisitForm, vitals_bp: e.target.value })}
            />
            <Input
              id="edit-visit-hr"
              label="Heart Rate"
              type="number"
              min={20}
              max={300}
              value={editVisitForm.vitals_hr}
              onChange={(e) => setEditVisitForm({ ...editVisitForm, vitals_hr: e.target.value })}
            />
            <Input
              id="edit-visit-spo2"
              label="SpO2 (%)"
              type="number"
              min={50}
              max={100}
              value={editVisitForm.vitals_spo2}
              onChange={(e) => setEditVisitForm({ ...editVisitForm, vitals_spo2: e.target.value })}
            />
            <Input
              id="edit-visit-wt"
              label="Weight (kg)"
              value={editVisitForm.vitals_weight_kg}
              onChange={(e) => setEditVisitForm({ ...editVisitForm, vitals_weight_kg: e.target.value })}
            />
          </div>
          <Textarea
            id="edit-visit-plan"
            label="Treatment Plan"
            rows={3}
            value={editVisitForm.treatment_plan}
            onChange={(e) => setEditVisitForm({ ...editVisitForm, treatment_plan: e.target.value })}
          />
          <div className="flex justify-end gap-2 pt-3 border-t border-border-warm">
            <Button variant="secondary" onClick={() => setEditingVisit(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Update Visit Record
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
