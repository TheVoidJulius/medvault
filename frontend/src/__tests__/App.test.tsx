import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import App from '../App';

const MOCK_USER = {
  id: 1,
  email: 'dr.sharma@medvault.edu',
  full_name: 'Dr. Ananya Sharma, MD',
  role_name: 'Doctor',
  is_active: true,
  doctor_profile: {
    id: 1,
    full_name: 'Dr. Ananya Sharma, MD',
    specialty: 'Internal Medicine',
    license_number: 'MCI-44102',
  },
};

function makePatientsList() {
  return [
    {
      id: 1,
      mrn: 'MV-2026-0001',
      first_name: 'Aarav',
      last_name: 'Mehta',
      date_of_birth: '1988-04-12',
      sex: 'Male',
      blood_group: 'O+',
      phone: '+91-9811100001',
      email: 'aarav.mehta@example.com',
      is_synthetic: true,
      is_active: true,
      visit_count: 3,
      last_visit_date: '2026-09-10T10:00:00Z',
      primary_conditions: ['Migraine without aura', 'Essential Hypertension'],
      active_allergies: ['Penicillin'],
    },
    {
      id: 2,
      mrn: 'MV-2026-0002',
      first_name: 'Diya',
      last_name: 'Kapoor',
      date_of_birth: '1992-08-21',
      sex: 'Female',
      blood_group: 'A+',
      phone: '+91-9811100002',
      email: 'diya.kapoor@example.com',
      is_synthetic: true,
      is_active: true,
      visit_count: 5,
      last_visit_date: '2026-09-14T11:30:00Z',
      primary_conditions: ['Type 2 Diabetes Mellitus'],
      active_allergies: [],
    },
    {
      id: 3,
      mrn: 'MV-2026-0003',
      first_name: 'Kabir',
      last_name: 'Nair',
      date_of_birth: '1979-01-05',
      sex: 'Male',
      blood_group: 'B+',
      phone: '+91-9811100003',
      email: 'kabir.nair@example.com',
      is_synthetic: true,
      is_active: true,
      visit_count: 2,
      last_visit_date: '2026-09-02T09:15:00Z',
      primary_conditions: ['Mild Persistent Asthma'],
      active_allergies: [],
    },
    {
      id: 4,
      mrn: 'MV-2026-0004',
      first_name: 'Isha',
      last_name: 'Desai',
      date_of_birth: '1995-11-19',
      sex: 'Female',
      blood_group: 'O+',
      phone: '+91-9811100004',
      email: 'isha.desai@example.com',
      is_synthetic: true,
      is_active: true,
      visit_count: 1,
      last_visit_date: '2026-08-29T16:00:00Z',
      primary_conditions: ['Iron Deficiency Anemia'],
      active_allergies: [],
    },
    {
      id: 5,
      mrn: 'MV-2026-0005',
      first_name: 'Rohan',
      last_name: 'Kulkarni',
      date_of_birth: '1968-06-30',
      sex: 'Male',
      blood_group: 'AB+',
      phone: '+91-9811100005',
      email: 'rohan.k@example.com',
      is_synthetic: true,
      is_active: true,
      visit_count: 4,
      last_visit_date: '2026-09-11T14:20:00Z',
      primary_conditions: ['Diabetic Neuropathy'],
      active_allergies: [],
    },
    {
      id: 6,
      mrn: 'MV-2026-0006',
      first_name: 'Meera',
      last_name: 'Iyer',
      date_of_birth: '1984-03-14',
      sex: 'Female',
      blood_group: 'B-',
      phone: '+91-9811100006',
      email: 'meera.iyer@example.com',
      is_synthetic: true,
      is_active: true,
      visit_count: 2,
      last_visit_date: '2026-09-08T13:10:00Z',
      primary_conditions: ['Hypothyroidism'],
      active_allergies: [],
    },
    {
      id: 7,
      mrn: 'MV-2026-0007',
      first_name: 'Vikram',
      last_name: 'Bhatia',
      date_of_birth: '1974-12-03',
      sex: 'Male',
      blood_group: 'O-',
      phone: '+91-9811100007',
      email: 'vikram.b@example.com',
      is_synthetic: true,
      is_active: true,
      visit_count: 6,
      last_visit_date: '2026-09-01T08:45:00Z',
      primary_conditions: ['Chronic Kidney Disease Stage 2'],
      active_allergies: [],
    },
    {
      id: 8,
      mrn: 'MV-2026-0008',
      first_name: 'Zara',
      last_name: 'Siddiqui',
      date_of_birth: '1990-07-22',
      sex: 'Female',
      blood_group: 'O+',
      phone: '+91-9811100008',
      email: 'zara.s@example.com',
      is_synthetic: true,
      is_active: true,
      visit_count: 1,
      last_visit_date: '2026-08-25T15:00:00Z',
      primary_conditions: ['Allergic Rhinitis'],
      active_allergies: [],
    },
  ];
}

function makePatientDetail() {
  return {
    id: 1,
    mrn: 'MV-2026-0001',
    first_name: 'Aarav',
    last_name: 'Mehta',
    date_of_birth: '1988-04-12',
    sex: 'Male',
    blood_group: 'O+',
    phone: '+91-9811100001',
    email: 'aarav.mehta@example.com',
    address: '14 Connaught Place, New Delhi',
    emergency_contact_name: 'Neha Mehta',
    emergency_contact_phone: '+91-9811199999',
    is_synthetic: true,
    is_active: true,
    created_at: '2025-01-10T09:00:00Z',
    updated_at: '2026-09-10T10:00:00Z',
    allergies: [
      {
        id: 1,
        patient_id: 1,
        allergen: 'Penicillin',
        reaction: 'Urticaria rash',
        severity: 'Severe',
        status: 'Active',
        recorded_at: '2025-02-01T10:00:00Z',
      },
    ],
    medical_history: [
      {
        id: 1,
        patient_id: 1,
        condition_name: 'Essential Hypertension',
        history_type: 'Chronic',
        onset_date: '2022-05-01',
        status: 'Active',
        notes: 'Managed on low-sodium diet.',
      },
    ],
    visits: [
      {
        id: 101,
        patient_id: 1,
        doctor_id: 1,
        doctor_name: 'Dr. Ananya Sharma, MD',
        visit_date: '2026-09-10T10:00:00Z',
        visit_type: 'OPD',
        chief_complaint: 'Recurring throbbing unilateral headaches',
        vitals_bp: '128/82',
        vitals_hr: 74,
        vitals_temp_c: '36.8',
        vitals_spo2: 99,
        vitals_weight_kg: '74.5',
        treatment_plan: 'Sumatriptan PRN and headache diary',
        follow_up_date: '2026-10-10',
        created_at: '2026-09-10T10:00:00Z',
        updated_at: '2026-09-10T10:00:00Z',
        symptoms: [
          { id: 1, visit_id: 101, name: 'Throbbing Headache', severity: 'Moderate', duration_days: 5, notes: 'Frontal' },
        ],
        diagnoses: [
          {
            id: 10,
            visit_id: 101,
            icd10_code: 'G43.909',
            condition_name: 'Migraine without aura',
            status: 'Active',
            diagnosed_date: '2026-09-10',
            notes: '',
          },
        ],
        prescriptions: [
          {
            id: 20,
            visit_id: 101,
            medication_id: 1,
            medication: { id: 1, name: 'Sumatriptan', generic_name: 'Sumatriptan', dosage_form: 'Tablet', strength: '50mg' },
            dosage: '50mg',
            frequency: 'PRN',
            duration_days: 14,
            route: 'Oral',
            instructions: 'Take at headache onset',
          },
        ],
        clinical_notes: [
          {
            id: 30,
            visit_id: 101,
            note_type: 'SOAP',
            content: 'Photophobia during episodes; neurological exam intact.',
            created_at: '2026-09-10T10:00:00Z',
          },
        ],
        test_results: [
          {
            id: 40,
            visit_id: 101,
            test_name: 'HbA1c',
            result_value: '5.4',
            unit: '%',
            reference_range: '4.0-5.6',
            abnormal_flag: 'Normal',
            tested_at: '2026-09-10T10:00:00Z',
            notes: '',
          },
        ],
      },
      {
        id: 102,
        patient_id: 1,
        doctor_id: 1,
        doctor_name: 'Dr. Ananya Sharma, MD',
        visit_date: '2026-07-04T09:30:00Z',
        visit_type: 'Follow-up',
        chief_complaint: 'Routine blood pressure follow-up',
        vitals_bp: '132/84',
        vitals_hr: 76,
        vitals_temp_c: '36.7',
        vitals_spo2: 98,
        vitals_weight_kg: '75.0',
        treatment_plan: 'Continue home BP monitoring',
        follow_up_date: '2026-09-04',
        created_at: '2026-07-04T09:30:00Z',
        updated_at: '2026-07-04T09:30:00Z',
        symptoms: [],
        diagnoses: [
          {
            id: 11,
            visit_id: 102,
            icd10_code: 'I10',
            condition_name: 'Essential Hypertension',
            status: 'Chronic',
            diagnosed_date: '2026-07-04',
            notes: '',
          },
        ],
        prescriptions: [],
        clinical_notes: [],
        test_results: [],
      },
    ],
  };
}

function createMockFetch() {
  const patients = makePatientsList();
  let detail = makePatientDetail();

  const summaryPayload = {
    patient_id: 1,
    patient_mrn: 'MV-2026-0001',
    patient_name: 'Aarav Mehta',
    generated_at: '2026-09-10T12:00:00Z',
    provider_used: 'deterministic-extractive-v1',
    cached: false,
    disclaimer: 'Clinician verification required before clinical action.',
    executive_overview: [
      {
        text: 'Patient presents with recurring migraine headaches and chronic hypertension.',
        citations: ['SYM-1'],
        severity_or_status: 'Moderate',
      },
    ],
    recurring_symptoms: [
      {
        text: 'Throbbing Headache persisted for 5 days across documented neurology review.',
        citations: ['SYM-1'],
        severity_or_status: 'Moderate',
      },
    ],
    active_and_past_diagnoses: [
      {
        text: 'Migraine without aura (ICD-10: G43.909).',
        citations: ['DX-10'],
        severity_or_status: 'Active',
      },
    ],
    medication_history: [
      {
        text: 'Sumatriptan 50mg PRN prescribed for acute migraine episodes.',
        citations: ['RX-20'],
        severity_or_status: 'Oral',
      },
    ],
    allergies_and_alerts: [
      {
        text: 'Active Severe allergy to Penicillin (Urticaria rash).',
        citations: ['ALG-1'],
        severity_or_status: 'Severe',
      },
    ],
    abnormal_test_trends: [],
    data_gaps_and_conflicts: [
      {
        text: 'No recent lipid panel recorded in the last 12 months.',
        citations: ['V-101'],
        severity_or_status: 'Gap',
      },
    ],
    chronological_timeline: [
      {
        visit_id: 101,
        visit_tag: 'V-101',
        visit_date: '2026-09-10',
        visit_type: 'OPD',
        doctor_name: 'Dr. Ananya Sharma, MD',
        chief_complaint: 'Recurring throbbing unilateral headaches',
        key_findings: 'Migraine workup complete',
        diagnoses: ['Migraine without aura'],
        prescriptions: ['Sumatriptan 50mg'],
        abnormal_labs: [],
      },
    ],
    citation_index: {
      'SYM-1': {
        tag: 'SYM-1',
        record_type: 'Symptom',
        record_id: 1,
        visit_id: 101,
        visit_date: '2026-09-10',
        label: 'Throbbing Headache (Moderate)',
        snippet: 'Throbbing Headache lasting 5 days; Frontal localization',
      },
      'DX-10': {
        tag: 'DX-10',
        record_type: 'Diagnosis',
        record_id: 10,
        visit_id: 101,
        visit_date: '2026-09-10',
        label: 'Migraine without aura',
        snippet: 'ICD-10 G43.909, Active',
      },
      'RX-20': {
        tag: 'RX-20',
        record_type: 'Prescription',
        record_id: 20,
        visit_id: 101,
        visit_date: '2026-09-10',
        label: 'Sumatriptan 50mg PRN',
        snippet: 'Take at headache onset',
      },
      'ALG-1': {
        tag: 'ALG-1',
        record_type: 'Allergy',
        record_id: 1,
        visit_id: null,
        visit_date: null,
        label: 'Penicillin (Severe)',
        snippet: 'Urticaria rash',
      },
      'V-101': {
        tag: 'V-101',
        record_type: 'Visit',
        record_id: 101,
        visit_id: 101,
        visit_date: '2026-09-10',
        label: 'OPD Visit',
        snippet: 'Recurring throbbing unilateral headaches',
      },
    },
    validation_stats: {
      total_citations_emitted: 5,
      verified_citations: 5,
      unverified_citations_dropped: 0,
      grounding_score: 1.0,
      source_records_indexed: 5,
    },
  };

  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const rawUrl = typeof input === 'string' ? input : input.toString();
    const url = new URL(rawUrl, 'http://localhost');
    const method = (init?.method || 'GET').toUpperCase();

    const jsonResponse = (body: unknown, status = 200) =>
      new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
      });

    if (url.pathname === '/api/auth/login' && method === 'POST') {
      const body = JSON.parse(String(init?.body || '{}'));
      const user = body.email === 'admin@medvault.edu' ? { ...MOCK_USER, id: 9, email: body.email, full_name: 'Pushkar Panwar', role_name: 'admin', doctor_profile: null } : MOCK_USER;
      return jsonResponse({
        access_token: 'mock-jwt-token-2026',
        token_type: 'bearer',
        user,
      });
    }

    if (url.pathname === '/api/dashboard/stats') {
      return jsonResponse({
        counts: {
          total_patients: patients.length,
          total_visits: 24,
          total_medical_records: 86,
          total_diagnoses: 18,
          total_prescriptions: 21,
          total_clinical_notes: 19,
          total_lab_results: 20,
          total_allergies: 8,
        },
        recent_visits: [
          {
            visit_id: 101,
            visit_tag: 'V-101',
            patient_id: 1,
            patient_name: 'Aarav Mehta',
            patient_mrn: 'MV-2026-0001',
            visit_date: '2026-09-10T10:00:00Z',
            visit_type: 'OPD',
            chief_complaint: 'Recurring throbbing unilateral headaches',
            primary_diagnosis: 'Migraine without aura',
            doctor_name: 'Dr. Ananya Sharma, MD',
          },
        ],
        recently_updated_records: [],
        top_conditions: [
          { condition: 'Migraine without aura', count: 6 },
          { condition: 'Essential Hypertension', count: 4 },
        ],
        top_symptoms: [
          { symptom: 'Throbbing Headache', count: 5 },
          { symptom: 'Fatigue', count: 3 },
        ],
      });
    }

    if (url.pathname === '/api/patients/medications/catalog') {
      return jsonResponse([
        { id: 1, name: 'Sumatriptan', generic_name: 'Sumatriptan', dosage_form: 'Tablet', strength: '50mg' },
      ]);
    }

    if (url.pathname === '/api/patients' && method === 'GET') {
      const search = (url.searchParams.get('q') || url.searchParams.get('search') || '').trim().toLowerCase();
      const sex = url.searchParams.get('sex') || '';
      const bloodGroup = url.searchParams.get('blood_group') || '';
      const filtered = patients.filter((p) => {
        if (sex && p.sex !== sex) return false;
        if (bloodGroup && p.blood_group !== bloodGroup) return false;
        if (search) {
          const hay = `${p.first_name} ${p.last_name} ${p.mrn} ${p.phone} ${p.primary_conditions.join(' ')}`.toLowerCase();
          if (!hay.includes(search)) return false;
        }
        return true;
      });
      return jsonResponse(filtered);
    }

    if (url.pathname === '/api/patients/1' && method === 'GET') {
      return jsonResponse(detail);
    }

    if (url.pathname === '/api/patients/1' && method === 'PUT') {
      const payload = JSON.parse(String(init?.body || '{}'));
      detail = { ...detail, ...payload };
      return jsonResponse(detail);
    }

    if (url.pathname === '/api/patients/1/allergies' && method === 'POST') {
      const payload = JSON.parse(String(init?.body || '{}'));
      const created = {
        id: detail.allergies.length + 10,
        patient_id: 1,
        recorded_at: '2026-09-15T10:00:00Z',
        ...payload,
      };
      detail = { ...detail, allergies: [...detail.allergies, created] };
      return jsonResponse(created, 201);
    }

    if (url.pathname === '/api/ai/patients/1/summary') {
      return jsonResponse(summaryPayload);
    }

    if (url.pathname === '/api/ai/query' && method === 'POST') {
      const body = JSON.parse(String(init?.body || '{}'));
      const q = String(body.query || '').toLowerCase();
      if (q.includes('nonexistentxyz')) {
        return jsonResponse({
          query: body.query,
          patient_id: body.patient_id ?? null,
          interpreted_filters: {
            target_record_types: ['Symptom', 'Diagnosis'],
            date_from: null,
            expanded_clinical_terms: ['nonexistentxyz'],
          },
          answer_statements: [
            {
              text: 'No stored clinical records matched the requested query.',
              citations: [],
              severity_or_status: 'Unavailable',
            },
          ],
          direct_summary: 'Insufficient clinical data found in stored records for this query.',
          retrieved_records: [],
          citation_index: {},
          provider_used: 'sql-keyword-matcher',
          disclaimer: 'Only stored database rows are queried.',
          total_matches: 0,
        });
      }
      return jsonResponse({
        query: body.query,
        patient_id: body.patient_id ?? null,
        interpreted_filters: {
          target_record_types: ['Symptom', 'Diagnosis'],
          date_from: '2024-01-01',
          expanded_clinical_terms: ['headache', 'migraine'],
        },
        answer_statements: [
          {
            text: 'Patient MV-2026-0001 reported Throbbing Headache during OPD consultation.',
            citations: ['SYM-1'],
            severity_or_status: 'Moderate',
          },
        ],
        direct_summary: '1 relational clinical record matched headache symptoms.',
        retrieved_records: [
          {
            citation_tag: 'SYM-1',
            record_type: 'Symptom',
            record_id: 1,
            visit_id: 101,
            patient_id: 1,
            patient_name: 'Aarav Mehta',
            patient_mrn: 'MV-2026-0001',
            visit_date: '2026-09-10',
            doctor_name: 'Dr. Ananya Sharma, MD',
            title: 'Throbbing Headache (Moderate)',
            details: 'Duration 5 days, frontal headache with photophobia.',
            relevance_score: 0.96,
            matched_terms: ['headache'],
          },
        ],
        citation_index: summaryPayload.citation_index,
        provider_used: 'sql-keyword-matcher',
        disclaimer: 'Derived strictly from SQL source records.',
        total_matches: 1,
      });
    }

    if (url.pathname === '/api/dashboard/public') {
      return jsonResponse({
        patients: 8, real_patients: 8, visits: 24, emergency_visits: 10, diagnoses: 18, distinct_conditions: 12,
        prescriptions: 21, lab_results: 20, abnormal_labs: 6, symptoms: 9, notes: 19, first_year: 2012, last_year: 2021,
        source: { name: 'MIMIC-IV Clinical Database Demo v2.2', institution: 'Beth Israel Deaconess Medical Center, Boston', license: 'Open Database License (ODbL)', url: 'https://physionet.org/content/mimic-iv-demo/2.2/' },
      });
    }

    if (url.pathname === '/api/auth/audit-logs') {
      return jsonResponse([
        { id: 1, created_at: '2026-11-27T08:00:00', user_name: 'Dr. Ananya Sharma, MD', user_role: 'doctor', action: 'AI_GENERATE_SUMMARY', detail: 'Summary for MV-2026-0001' },
      ]);
    }

    return jsonResponse({ detail: `Unhandled mock route: ${method} ${url.pathname}` }, 404);
  });
}

async function signInAsDoctor() {
  window.location.hash = '#/sign-in';
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /Dr\. Ananya Sharma, MD/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
  await waitFor(() => expect(screen.getByRole('heading', { name: /Overview for Ananya/ })).toBeInTheDocument());
}

async function openAaravChart() {
  fireEvent.click(screen.getByRole('button', { name: 'Patients' }));
  const main = screen.getByRole('main');
  await waitFor(() => expect(within(main).getByText('Aarav Mehta')).toBeInTheDocument());
  fireEvent.click(within(main).getByRole('button', { name: 'Open chart for Aarav Mehta' }));
  await waitFor(() => expect(within(main).getByRole('heading', { level: 1, name: 'Aarav Mehta' })).toBeInTheDocument());
  return main;
}

describe('MedVault AI frontend', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows the landing page to visitors and opens sign-in from it', async () => {
    window.location.hash = '';
    render(<App />);
    expect(screen.getByRole('heading', { name: /Every record, read back with its sources/i })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('real patients')).toBeInTheDocument());
    expect(screen.getAllByText('Beth Israel Deaconess Medical Center, Boston', { exact: false }).length).toBeGreaterThan(0);
    fireEvent.click(screen.getAllByRole('button', { name: /Open the records/i })[0]);
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
    expect(window.location.hash).toBe('#/sign-in');
  });

  it('gives the admin a records-administration home with completeness and activity', async () => {
    window.location.hash = '#/sign-in';
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /Pushkar Panwar/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    await waitFor(() => expect(screen.getByRole('heading', { name: /Records administration/ })).toBeInTheDocument());
    const main = screen.getByRole('main');
    expect(within(main).getByText('Data completeness')).toBeInTheDocument();
    await waitFor(() => expect(within(main).getByText('Blood group recorded')).toBeInTheDocument());
    await waitFor(() => expect(within(main).getByText('Generated AI summary')).toBeInTheDocument());
  });

  it('keeps the session token in sessionStorage only', async () => {
    await signInAsDoctor();
    expect(sessionStorage.getItem('medvault_token')).toBe('mock-jwt-token-2026');
    expect(localStorage.getItem('medvault_token')).toBeNull();
  });

  it('shows record counts and charts on the overview and switches theme', async () => {
    await signInAsDoctor();
    const main = screen.getByRole('main');
    expect(within(main).getByText('Diagnoses').nextSibling).toHaveTextContent('18');
    expect(within(main).getByText('6 dx')).toBeInTheDocument();
    expect(within(main).getByText('Visits per month')).toBeInTheDocument();
    expect(within(main).getByText('Recurring throbbing unilateral headaches')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Switch to dark theme' }));
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    expect(localStorage.getItem('medvault_theme')).toBe('dark');
    fireEvent.click(screen.getByRole('button', { name: 'Switch to light theme' }));
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('searches, filters and sorts the patient list and recovers from an empty result', async () => {
    await signInAsDoctor();
    fireEvent.click(screen.getByRole('button', { name: 'Patients' }));
    const main = screen.getByRole('main');
    await waitFor(() => expect(within(main).getByText('Zara Siddiqui')).toBeInTheDocument());
    expect(within(main).getByText('Vikram Bhatia')).toBeInTheDocument();

    fireEvent.change(within(main).getByLabelText('Filter by sex'), { target: { value: 'Female' } });
    fireEvent.change(within(main).getByLabelText('Filter by blood group'), { target: { value: 'O+' } });
    fireEvent.change(within(main).getByLabelText('Sort patients'), { target: { value: 'name' } });
    const names = within(main)
      .getAllByRole('button', { name: /^Open chart for/ })
      .map((b) => b.textContent);
    expect(names).toEqual(['Isha Desai', 'Zara Siddiqui']);

    fireEvent.change(within(main).getByLabelText('Search patients'), { target: { value: 'zzzzz-no-patient' } });
    expect(within(main).getByText('No patient matches')).toBeInTheDocument();
    fireEvent.click(within(main).getByRole('button', { name: 'Clear search and filters' }));
    expect(within(main).getByText('Aarav Mehta')).toBeInTheDocument();
  });

  it('edits demographics, records an allergy and filters the visit timeline', async () => {
    await signInAsDoctor();
    const main = await openAaravChart();
    expect(within(main).getByText('MV-2026-0001')).toBeInTheDocument();

    fireEvent.click(within(main).getByRole('button', { name: /Edit profile/ }));
    const dialog = screen.getByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText(/^Mobile/), { target: { value: '+91-99999-88888' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Save changes' }));
    await waitFor(() => expect(within(main).getByText('+91-99999-88888')).toBeInTheDocument());

    fireEvent.click(within(main).getByRole('button', { name: /Add allergy/ }));
    const allergyDialog = screen.getByRole('dialog');
    fireEvent.change(within(allergyDialog).getByLabelText(/^Allergen/), { target: { value: 'Sulfa Drugs' } });
    fireEvent.change(within(allergyDialog).getByLabelText(/^Reaction/), { target: { value: 'Stevens-Johnson risk' } });
    fireEvent.click(within(allergyDialog).getByRole('button', { name: 'Record allergy' }));
    await waitFor(() => expect(within(main).getByText(/Allergy: Sulfa Drugs/)).toBeInTheDocument());

    // The chart opens on Overview; visits live in their own tab.
    fireEvent.click(within(main).getByRole('tab', { name: /Visits/ }));
    expect(within(main).getByText('Recurring throbbing unilateral headaches')).toBeInTheDocument();
    expect(within(main).getByText('Routine blood pressure follow-up')).toBeInTheDocument();

    // Older visits start collapsed to a one-line summary and expand on click.
    const older = within(main).getByRole('button', { name: /Expand visit V-\d+: Routine blood pressure follow-up/ });
    expect(older).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(older);
    expect(within(main).getByRole('button', { name: /Collapse visit V-\d+: Routine blood pressure follow-up/ })).toHaveAttribute('aria-expanded', 'true');

    fireEvent.change(within(main).getByLabelText('Filter by visit type'), { target: { value: 'Follow-up' } });
    expect(within(main).queryByText('Recurring throbbing unilateral headaches')).not.toBeInTheDocument();
    expect(within(main).getByText('Routine blood pressure follow-up')).toBeInTheDocument();
  });

  it('groups lab results and medicines across visits', async () => {
    await signInAsDoctor();
    const main = await openAaravChart();
    fireEvent.click(within(main).getByRole('tab', { name: /Lab results/ }));
    expect(within(main).getByRole('columnheader', { name: 'Latest result' })).toBeInTheDocument();
    expect(within(main).getAllByRole('row').length).toBeGreaterThan(1);
    fireEvent.click(within(main).getByRole('tab', { name: /Medicines/ }));
    expect(within(main).getByRole('columnheader', { name: 'Last dose and how often' })).toBeInTheDocument();
  });

  it('opens the cited source row from an AI summary and flags a statement', async () => {
    await signInAsDoctor();
    const main = await openAaravChart();
    fireEvent.click(within(main).getByRole('tab', { name: /AI summary/ }));
    await waitFor(() => expect(within(main).getByText(/Patient presents with recurring migraine headaches/i)).toBeInTheDocument());

    fireEvent.click(within(main).getAllByRole('button', { name: 'Inspect source record SYM-1' })[0]);
    const drawer = screen.getByRole('dialog', { name: 'Citation source record inspector' });
    expect(within(drawer).getByText('Throbbing Headache (Moderate)')).toBeInTheDocument();
    fireEvent.click(within(drawer).getByRole('button', { name: 'Close source record inspector' }));
    expect(screen.queryByRole('dialog', { name: 'Citation source record inspector' })).not.toBeInTheDocument();

    fireEvent.click(within(main).getAllByRole('button', { name: 'Flag for review' })[0]);
    expect(within(main).getByRole('button', { name: 'Flagged for review' })).toHaveAttribute('aria-pressed', 'true');
    expect(within(main).getByText('Flagged for review: 1')).toBeInTheDocument();
  });

  it('answers a records question with sources and refuses when nothing matches', async () => {
    await signInAsDoctor();
    fireEvent.click(screen.getByRole('button', { name: 'Ask the records' }));
    const main = screen.getByRole('main');
    await waitFor(() => expect(within(main).getByText('1 matching record')).toBeInTheDocument());
    expect(within(main).getByText('Source records (1)')).toBeInTheDocument();
    expect(within(main).getByText('Throbbing Headache (Moderate)')).toBeInTheDocument();

    fireEvent.change(within(main).getByLabelText('Question about the records'), { target: { value: 'Find nonexistentxyz symptom in history' } });
    fireEvent.click(within(main).getByRole('button', { name: 'Ask' }));
    await waitFor(() => expect(within(main).getByText('Nothing in the record matches')).toBeInTheDocument());
    expect(within(main).getByText('0 matching records')).toBeInTheDocument();
  });

  it('finds a patient from the command palette', async () => {
    await signInAsDoctor();
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining('/api/patients'), expect.anything()));
    fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    const palette = screen.getByRole('dialog', { name: 'Command palette' });
    fireEvent.change(within(palette).getByLabelText('Search patients and commands'), { target: { value: 'aarav' } });
    await waitFor(() => expect(within(palette).getByText('Aarav Mehta')).toBeInTheDocument());
    fireEvent.keyDown(within(palette).getByLabelText('Search patients and commands'), { key: 'Enter' });
    await waitFor(() => expect(screen.getByRole('heading', { level: 1, name: 'Aarav Mehta' })).toBeInTheDocument());
    expect(window.location.hash).toBe('#/patients/1/overview');
  });
});
