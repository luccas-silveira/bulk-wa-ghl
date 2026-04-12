/**
 * Campaign Wizard Component - GoHighLevel Integration
 *
 * Updated to use GoHighLevel (GHL) locations for WhatsApp messaging.
 * Migrated from WAHA to GHL Conversations API.
 */

import React, { useState } from 'react';
import Papa from 'papaparse';
import { parsePhoneNumber, isValidPhoneNumber } from 'libphonenumber-js';
import { CampaignFormData, CampaignCreateRequest, ContactCsvData, SendingSpeed, ScheduleType } from '../../types/api';
import { useGHLUsers } from '../../hooks/useGHLUsers';
import { useToast } from '../ui/Toast';

interface CampaignWizardProps {
  onSubmit: (campaign: CampaignCreateRequest) => Promise<void>;
  onCancel: () => void;
}

const CampaignWizard: React.FC<CampaignWizardProps> = ({ onSubmit, onCancel }) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<CampaignFormData>({
    name: '',
    ghl_location_id: '',
    ghl_user_ids: [],  // Multiple users for round-robin
    sending_speed: 'medium',
    schedule_type: 'immediate',
    messages: [{ text: '', media_url: '' }],
    audience_type: 'csv_upload',  // CSV como padrão
    tag_filters: { logic: 'AND', selected_tags: [] },
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [parsedContacts, setParsedContacts] = useState<ContactCsvData[]>([]);
  const [csvParseError, setCsvParseError] = useState<string | null>(null);

  // Column mapping state
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [csvRawData, setCsvRawData] = useState<Record<string, string>[]>([]);
  const [columnMapping, setColumnMapping] = useState<{
    phone: string;
    name: string;
    email: string;
  }>({
    phone: '',
    name: '',
    email: ''
  });
  const [showMapping, setShowMapping] = useState(false);

  // Toast hook
  const { addToast } = useToast();

  const stepHeadingRef = React.useRef<HTMLHeadingElement>(null);

  // Load users for fixed location
  const { users, loading: usersLoading, error: usersError } = useGHLUsers({
    locationId: formData.ghl_location_id,
    autoFetch: true,
  });

  // Check if form is dirty (has unsaved changes)
  const isDirty = React.useMemo(() => {
    return (
      formData.name.trim().length > 0 ||
      (formData.ghl_user_ids?.length ?? 0) > 0 ||
      formData.messages.some((m) => m.text.trim() || (m.media_url ?? '').trim()) ||
      parsedContacts.length > 0
    );
  }, [formData, parsedContacts]);

  // Show beforeunload warning when form is dirty
  React.useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty]);

  React.useEffect(() => {
    stepHeadingRef.current?.focus();
  }, [currentStep]);

  // Handle CSV file upload and parsing
  const MAX_CSV_SIZE_MB = 10;
  const MAX_CONTACT_COUNT = 10_000;

  const handleCsvUpload = (file: File | undefined) => {
    if (!file) {
      setParsedContacts([]);
      setCsvParseError(null);
      setCsvHeaders([]);
      setCsvRawData([]);
      setShowMapping(false);
      setFormData(prev => ({ ...prev, csv_file: undefined }));
      return;
    }

    if (file.size > MAX_CSV_SIZE_MB * 1024 * 1024) {
      setCsvParseError(`Arquivo excede o limite de ${MAX_CSV_SIZE_MB}MB`);
      return;
    }

    setFormData(prev => ({ ...prev, csv_file: file }));
    setCsvParseError(null);

    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        try {
          if (!results.meta.fields || results.meta.fields.length === 0) {
            setCsvParseError('CSV não contém cabeçalhos (headers)');
            return;
          }

          if (results.data.length > MAX_CONTACT_COUNT) {
            setCsvParseError(`CSV contém ${results.data.length} linhas, excedendo o limite de ${MAX_CONTACT_COUNT.toLocaleString()} contatos`);
            return;
          }

          // Store headers and raw data
          setCsvHeaders(results.meta.fields);
          setCsvRawData(results.data as Record<string, string>[]);

          // Try to auto-detect common column names
          const headers = results.meta.fields.map(h => h.toLowerCase());
          const autoMapping = {
            phone: '',
            name: '',
            email: ''
          };

          // Auto-detect phone column
          const phonePatterns = ['telefone', 'phone', 'celular', 'whatsapp', 'número', 'numero'];
          const phoneCol = results.meta.fields.find((h, i) =>
            phonePatterns.some(p => headers[i].includes(p))
          );
          if (phoneCol) autoMapping.phone = phoneCol;

          // Auto-detect name column
          const namePatterns = ['nome', 'name', 'contact', 'contato'];
          const nameCol = results.meta.fields.find((h, i) =>
            namePatterns.some(p => headers[i].includes(p))
          );
          if (nameCol) autoMapping.name = nameCol;

          // Auto-detect email column
          const emailPatterns = ['email', 'e-mail', 'mail'];
          const emailCol = results.meta.fields.find((h, i) =>
            emailPatterns.some(p => headers[i].includes(p))
          );
          if (emailCol) autoMapping.email = emailCol;

          setColumnMapping(autoMapping);
          setShowMapping(true);

        } catch (error) {
          setCsvParseError('Erro ao processar arquivo CSV');
        }
      },
      error: (error) => {
        setCsvParseError(`Erro ao ler arquivo: ${error.message}`);
      }
    });
  };

  // Apply column mapping to generate contacts
  const applyColumnMapping = () => {
    if (!columnMapping.phone) {
      setCsvParseError('Você deve selecionar a coluna de Telefone');
      return;
    }

    const contacts: ContactCsvData[] = [];
    const errors: string[] = [];

    csvRawData.forEach((row: Record<string, string>, index: number) => {
      const phoneNumber = row[columnMapping.phone];
      const name = columnMapping.name ? row[columnMapping.name] : '';
      const email = columnMapping.email ? row[columnMapping.email] : '';

      if (!phoneNumber) {
        errors.push(`Linha ${index + 2}: Telefone vazio`);
        return;
      }

      // Normalize phone to E.164; keep original if unparseable (backend tolerates both)
      const rawPhone = String(phoneNumber).trim();
      let normalizedPhone = rawPhone;
      try {
        const parsed = parsePhoneNumber(rawPhone);
        if (parsed && parsed.isValid()) {
          normalizedPhone = parsed.format('E.164');
        }
      } catch {
        // parsePhoneNumber throws for invalid input; keep rawPhone as-is
      }

      contacts.push({
        phone_number: normalizedPhone,
        name: name ? String(name).trim() : '',
        email: email ? String(email).trim() : undefined,
      });
    });

    if (errors.length > 0) {
      setCsvParseError(`Erros encontrados:\n${errors.slice(0, 5).join('\n')}${errors.length > 5 ? `\n... e mais ${errors.length - 5} erros` : ''}`);
    } else {
      setCsvParseError(null); // clear any stale error from a previous failed parse
    }

    if (contacts.length === 0) {
      setCsvParseError('Nenhum contato válido encontrado no CSV');
      setParsedContacts([]);
    } else {
      setParsedContacts(contacts);
      setShowMapping(false);
    }
  };

  // Form validation
  const validateStep = (step: number): boolean => {
    const newErrors: Record<string, string> = {};

    switch (step) {
      case 1: // Basic Info
        if (!formData.name.trim()) {
          newErrors.name = 'Nome da campanha é obrigatório';
        }
        if (!formData.ghl_user_ids || formData.ghl_user_ids.length === 0) {
          newErrors.ghl_user_ids = 'Por favor, selecione pelo menos um usuário';
        }
        break;

      case 2: // Messages
        // At least one message with text OR media is required
        const hasValidMessage = formData.messages.some(msg =>
          msg.text.trim() || msg.media_url?.trim()
        );

        if (formData.messages.length === 0 || !hasValidMessage) {
          newErrors.messages = 'Pelo menos uma mensagem (texto ou mídia) é obrigatória';
        }
        if (formData.messages.length > 3) {
          newErrors.messages = 'Máximo de 3 mensagens permitidas';
        }
        break;

      case 3: // Audience - CSV Only
        if (!formData.csv_file) {
          newErrors.csv_file = 'Por favor, faça upload de um arquivo CSV';
        } else if (parsedContacts.length === 0) {
          newErrors.csv_file = 'Arquivo CSV não possui contatos válidos';
        } else if (csvParseError) {
          newErrors.csv_file = 'Arquivo CSV possui erros';
        }
        break;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async () => {
    if (!validateStep(3)) return;

    // Guard: ensure at least one message has text or media_url before submitting
    const validMessages = formData.messages.filter(
      (msg) => msg.text.trim() || (msg.media_url ?? '').trim()
    );
    if (validMessages.length === 0) {
      setErrors((prev) => ({
        ...prev,
        messages: 'Pelo menos uma mensagem com texto ou URL de mídia é obrigatória',
      }));
      return;
    }

    setLoading(true);
    try {
      const campaignRequest: CampaignCreateRequest = {
        name: formData.name,
        ghl_location_id: formData.ghl_location_id,  // Changed from waha_session_id
        ghl_user_ids: formData.ghl_user_ids,  // Multiple users for round-robin
        sending_speed: formData.sending_speed,
        schedule_type: formData.schedule_type,
        scheduled_time: formData.scheduled_time?.toISOString(),
        messages: validMessages.map((msg, index) => ({
          text: msg.text,
          media_url: msg.media_url || undefined,
          order: index + 1,
        })),
        audience_criteria: {
          csv_data: parsedContacts,
        },
      };

      await onSubmit(campaignRequest);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Erro desconhecido ao criar campanha';
      addToast({
        type: 'error',
        title: 'Erro ao criar campanha',
        message,
      });
    } finally {
      setLoading(false);
    }
  };

  // Navigation
  const nextStep = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, 4));
    }
  };

  const prevStep = () => {
    setErrors({});
    setCurrentStep(prev => Math.max(prev - 1, 1));
  };


  return (
    <div className="max-w-2xl mx-auto p-6">
      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {[1, 2, 3, 4].map((step) => (
            <div key={step} className="flex items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  step <= currentStep
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-600'
                }`}
              >
                {step}
              </div>
              {step < 4 && (
                <div
                  className={`w-16 h-1 mx-2 ${
                    step < currentStep ? 'bg-blue-600' : 'bg-gray-200'
                  }`}
                />
              )}
            </div>
          ))}
        </div>
        <div className="flex justify-between mt-2 text-xs text-gray-600">
          <span>Informações</span>
          <span>Mensagens</span>
          <span>Contatos</span>
          <span>Revisão</span>
        </div>
      </div>

      <form onSubmit={(e) => e.preventDefault()}>
        {/* Step 1: Basic Information */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <h2 ref={stepHeadingRef} tabIndex={-1} className="text-xl font-semibold text-gray-900">Detalhes da Campanha</h2>

            {/* Campaign Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nome da Campanha *
              </label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className={`w-full px-3 py-2 border rounded-md ${errors.name ? 'border-red-300' : 'border-gray-300'}`}
                placeholder="Digite o nome da campanha"
                required
              />
              {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name}</p>}
            </div>

            {/* GHL User Selection - Dropdown Multi-select */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Usuários (Envio Round-Robin) *
              </label>
              {usersLoading ? (
                <div className="animate-pulse">
                  <div className="h-10 bg-gray-200 rounded"></div>
                </div>
              ) : usersError ? (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-800 text-sm">Erro ao carregar usuários: {usersError}</p>
                </div>
              ) : users.length === 0 ? (
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-yellow-800 text-sm">Nenhum usuário encontrado para esta localização</p>
                </div>
              ) : (
                <div className="relative">
                  {/* Selected users display with chips */}
                  <div className={`min-h-[42px] w-full px-3 py-2 border rounded-md bg-white flex flex-wrap gap-2 items-center ${errors.ghl_user_ids ? 'border-red-300' : 'border-gray-300'}`}>
                    {formData.ghl_user_ids && formData.ghl_user_ids.length > 0 ? (
                      formData.ghl_user_ids.map((userId) => {
                        const user = users.find(u => u.ghl_user_id === userId);
                        return user ? (
                          <span key={userId} className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded">
                            {user.name}
                            <button
                              type="button"
                              onClick={() => {
                                setFormData(prev => ({
                                  ...prev,
                                  ghl_user_ids: prev.ghl_user_ids?.filter(id => id !== userId) || []
                                }));
                              }}
                              className="text-blue-600 hover:text-blue-800"
                            >
                              ×
                            </button>
                          </span>
                        ) : null;
                      })
                    ) : (
                      <span className="text-gray-500 text-sm">Selecione os usuários...</span>
                    )}
                  </div>

                  {/* Dropdown with checkboxes */}
                  <details className="mt-2">
                    <summary className="cursor-pointer px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded text-sm font-medium text-gray-700">
                      {formData.ghl_user_ids && formData.ghl_user_ids.length > 0
                        ? `${formData.ghl_user_ids.length} selecionado(s) - Clique para editar`
                        : 'Clique para selecionar usuários'}
                    </summary>
                    <div className="mt-2 border border-gray-300 rounded-md bg-white max-h-60 overflow-y-auto">
                      {users.map((user) => (
                        <label
                          key={user.ghl_user_id}
                          className="flex items-center space-x-3 px-4 py-2 hover:bg-gray-50 cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={formData.ghl_user_ids?.includes(user.ghl_user_id) || false}
                            onChange={(e) => {
                              const isChecked = e.target.checked;
                              setFormData(prev => {
                                const currentIds = prev.ghl_user_ids || [];
                                if (isChecked) {
                                  return { ...prev, ghl_user_ids: [...currentIds, user.ghl_user_id] };
                                } else {
                                  return { ...prev, ghl_user_ids: currentIds.filter(id => id !== user.ghl_user_id) };
                                }
                              });
                            }}
                            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                          />
                          <span className="text-sm text-gray-700">
                            {user.name} {user.email ? `(${user.email})` : ''}
                          </span>
                        </label>
                      ))}
                    </div>
                  </details>
                </div>
              )}
              {errors.ghl_user_ids && <p className="mt-1 text-sm text-red-600">{errors.ghl_user_ids}</p>}
              <p className="mt-1 text-xs text-gray-500">
                {formData.ghl_user_ids && formData.ghl_user_ids.length > 0
                  ? `${formData.ghl_user_ids.length} ${formData.ghl_user_ids.length === 1 ? 'usuário' : 'usuários'}. Cada um enviará 1 mensagem por vez em ordem sequencial.`
                  : 'Os usuários enviarão mensagens em ordem sequencial (round-robin).'}
              </p>
            </div>

            {/* Sending Speed */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Velocidade de Envio
              </label>
              <select
                value={formData.sending_speed}
                onChange={(e) => setFormData(prev => ({ ...prev, sending_speed: e.target.value as SendingSpeed }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="slow">Lenta (Conservadora)</option>
                <option value="medium">Média (Recomendada)</option>
                <option value="fast">Rápida (Agressiva)</option>
              </select>
            </div>

            {/* Schedule Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Agendamento
              </label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="schedule_type"
                    value="immediate"
                    checked={formData.schedule_type === 'immediate'}
                    onChange={(e) => setFormData(prev => ({ ...prev, schedule_type: e.target.value as ScheduleType }))}
                    className="mr-2"
                  />
                  Enviar imediatamente
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="schedule_type"
                    value="scheduled"
                    checked={formData.schedule_type === 'scheduled'}
                    onChange={(e) => setFormData(prev => ({ ...prev, schedule_type: e.target.value as ScheduleType }))}
                    className="mr-2"
                  />
                  Agendar para depois
                </label>
              </div>

              {formData.schedule_type === 'scheduled' && (
                <input
                  type="datetime-local"
                  value={formData.scheduled_time?.toISOString().slice(0, 16) || ''}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    scheduled_time: e.target.value ? new Date(e.target.value) : undefined
                  }))}
                  className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              )}
            </div>
          </div>
        )}

        {/* Step 2: Messages */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <h2 ref={stepHeadingRef} tabIndex={-1} className="text-xl font-semibold text-gray-900">Mensagens da Campanha</h2>
            <p className="text-sm text-gray-600">Adicione até 3 mensagens para sua campanha</p>

            {formData.messages.map((message, index) => (
              <div key={index} className="p-4 border border-gray-200 rounded-lg">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="font-medium">Mensagem {index + 1}</h3>
                  {formData.messages.length > 1 && (
                    <button
                      type="button"
                      onClick={() => {
                        const newMessages = formData.messages.filter((_, i) => i !== index);
                        setFormData(prev => ({ ...prev, messages: newMessages }));
                      }}
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Remover
                    </button>
                  )}
                </div>

                <textarea
                  value={message.text}
                  onChange={(e) => {
                    const newMessages = [...formData.messages];
                    newMessages[index].text = e.target.value;
                    setFormData(prev => ({ ...prev, messages: newMessages }));
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  rows={3}
                  placeholder="Digite o texto da mensagem (opcional se houver mídia)"
                />

                <input
                  type="url"
                  value={message.media_url || ''}
                  onChange={(e) => {
                    const newMessages = [...formData.messages];
                    newMessages[index].media_url = e.target.value;
                    setFormData(prev => ({ ...prev, messages: newMessages }));
                  }}
                  className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="URL da mídia (opcional se houver texto)"
                />
              </div>
            ))}

            {formData.messages.length < 3 && (
              <button
                type="button"
                onClick={() => {
                  setFormData(prev => ({
                    ...prev,
                    messages: [...prev.messages, { text: '', media_url: '' }]
                  }));
                }}
                className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-gray-400"
              >
                + Adicionar Outra Mensagem
              </button>
            )}

            {errors.messages && <p className="text-sm text-red-600">{errors.messages}</p>}
          </div>
        )}

        {/* Step 3: Audience - CSV Upload with Column Mapping */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <h2 ref={stepHeadingRef} tabIndex={-1} className="text-xl font-semibold text-gray-900">Upload de Contatos</h2>
            <p className="text-sm text-gray-600">Faça upload de um arquivo CSV e mapeie as colunas</p>

            <div className="space-y-4">
              {/* File Upload */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Arquivo CSV *
                </label>
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => handleCsvUpload(e.target.files?.[0])}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Qualquer CSV com cabeçalhos. Você poderá mapear as colunas na próxima etapa.
                </p>
              </div>

              {/* Column Mapping Interface */}
              {showMapping && csvHeaders.length > 0 && (
                <div className="border border-blue-200 bg-blue-50 rounded-lg p-4 space-y-4">
                  <h3 className="font-medium text-blue-900">Mapeamento de Colunas</h3>
                  <p className="text-sm text-blue-700">
                    Detectamos {csvHeaders.length} colunas. Mapeie-as para os campos necessários:
                  </p>

                  {/* Phone Mapping */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Telefone (obrigatório) *
                    </label>
                    <select
                      value={columnMapping.phone}
                      onChange={(e) => setColumnMapping(prev => ({ ...prev, phone: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                    >
                      <option value="">Selecione a coluna...</option>
                      {csvHeaders.map((header) => (
                        <option key={header} value={header}>
                          {header}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Name Mapping */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Nome (opcional)
                    </label>
                    <select
                      value={columnMapping.name}
                      onChange={(e) => setColumnMapping(prev => ({ ...prev, name: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                    >
                      <option value="">Não mapear</option>
                      {csvHeaders.map((header) => (
                        <option key={header} value={header}>
                          {header}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Email Mapping */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Email (opcional)
                    </label>
                    <select
                      value={columnMapping.email}
                      onChange={(e) => setColumnMapping(prev => ({ ...prev, email: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                    >
                      <option value="">Não mapear</option>
                      {csvHeaders.map((header) => (
                        <option key={header} value={header}>
                          {header}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Preview First Row */}
                  {csvRawData.length > 0 && (
                    <div className="mt-3 p-3 bg-white border border-gray-200 rounded">
                      <p className="text-xs font-medium text-gray-700 mb-2">Preview (primeira linha):</p>
                      <div className="text-xs text-gray-600 space-y-1">
                        {columnMapping.phone && (
                          <div>
                            <strong>Telefone:</strong> {csvRawData[0][columnMapping.phone] || '(vazio)'}
                          </div>
                        )}
                        {columnMapping.name && (
                          <div>
                            <strong>Nome:</strong> {csvRawData[0][columnMapping.name] || '(vazio)'}
                          </div>
                        )}
                        {columnMapping.email && (
                          <div>
                            <strong>Email:</strong> {csvRawData[0][columnMapping.email] || '(vazio)'}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Apply Button */}
                  <button
                    type="button"
                    onClick={applyColumnMapping}
                    disabled={!columnMapping.phone}
                    className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                  >
                    Aplicar Mapeamento
                  </button>
                </div>
              )}

              {/* CSV Parse Error */}
              {csvParseError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-sm text-red-800 whitespace-pre-line">{csvParseError}</p>
                </div>
              )}

              {/* CSV Success Preview */}
              {parsedContacts.length > 0 && !csvParseError && !showMapping && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-md">
                  <p className="text-sm font-medium text-green-800 mb-2">
                    ✓ {parsedContacts.length} contato{parsedContacts.length !== 1 ? 's' : ''} carregado{parsedContacts.length !== 1 ? 's' : ''}
                  </p>
                  <div className="text-xs text-green-700 space-y-1">
                    {parsedContacts.slice(0, 3).map((contact, idx) => (
                      <div key={idx}>
                        • {contact.phone_number} {contact.name ? `- ${contact.name}` : ''}
                      </div>
                    ))}
                    {parsedContacts.length > 3 && (
                      <div className="text-green-600">+ {parsedContacts.length - 3} mais...</div>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowMapping(true)}
                    className="mt-2 text-sm text-blue-600 hover:text-blue-800"
                  >
                    Remapear colunas
                  </button>
                </div>
              )}

              {errors.csv_file && <p className="text-sm text-red-600">{errors.csv_file}</p>}
            </div>
          </div>
        )}

        {/* Step 4: Review */}
        {currentStep === 4 && (
          <div className="space-y-6">
            <h2 ref={stepHeadingRef} tabIndex={-1} className="text-xl font-semibold text-gray-900">Revisar Campanha</h2>

            <div className="bg-gray-50 p-4 rounded-lg space-y-3">
              <div>
                <span className="font-medium">Campanha:</span> {formData.name}
              </div>
              <div>
                <span className="font-medium">Usuários:</span> {
                  formData.ghl_user_ids && formData.ghl_user_ids.length > 0
                    ? `${formData.ghl_user_ids.length} selecionado(s)`
                    : 'Nenhum'
                }
              </div>
              <div>
                <span className="font-medium">Mensagens:</span> {formData.messages.filter(m => m.text.trim()).length}
              </div>
              <div>
                <span className="font-medium">Contatos:</span> {parsedContacts.length}
              </div>
              <div>
                <span className="font-medium">Agendamento:</span> {
                  formData.schedule_type === 'immediate' ? 'Enviar imediatamente' : 'Agendado'
                }
              </div>
              <div>
                <span className="font-medium">Velocidade:</span> {
                  formData.sending_speed === 'slow' ? 'Lenta' :
                  formData.sending_speed === 'medium' ? 'Média' : 'Rápida'
                }
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between mt-8">
          <div>
            {currentStep > 1 && (
              <button
                type="button"
                onClick={prevStep}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Anterior
              </button>
            )}
          </div>

          <div className="space-x-3">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancelar
            </button>

            {currentStep < 4 ? (
              <button
                type="button"
                onClick={nextStep}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Próximo
              </button>
            ) : (
              <button
                type="submit"
                onClick={handleSubmit}
                disabled={loading}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {loading ? 'Criando...' : 'Criar Campanha'}
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  );
};

export default CampaignWizard;