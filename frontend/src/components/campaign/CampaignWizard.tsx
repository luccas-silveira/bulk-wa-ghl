/**
 * Campaign Wizard Component - WhatsApp Campaign Interface Improvements
 *
 * Updated to use WAHA session dropdown instead of separate channel/user/team fields.
 * Removes GHL Team ID field and consolidates WhatsApp channel selection.
 */

import React, { useState, useEffect } from 'react';
import { CampaignFormData, WAHASession, CampaignCreateRequest } from '../../types/api';
import { wahaSessionService } from '../../services/waha-session-service';

interface CampaignWizardProps {
  onSubmit: (campaign: CampaignCreateRequest) => Promise<void>;
  onCancel: () => void;
}

const CampaignWizard: React.FC<CampaignWizardProps> = ({ onSubmit, onCancel }) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState<WAHASession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [formData, setFormData] = useState<CampaignFormData>({
    name: '',
    waha_session_id: '',
    sending_speed: 'medium',
    schedule_type: 'immediate',
    messages: [{ text: '', media_url: '' }],
    audience_type: 'all_contacts',
    tag_filters: { logic: 'AND', selected_tags: [] },
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Load WAHA sessions on component mount
  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    setSessionsLoading(true);
    try {
      const activeSessions = await wahaSessionService.getActiveSessions();
      setSessions(activeSessions);

      // Auto-select if only one active session
      if (activeSessions.length === 1) {
        setFormData(prev => ({
          ...prev,
          waha_session_id: activeSessions[0].id
        }));
      }
    } catch (error) {
      console.error('Failed to load WAHA sessions:', error);
    } finally {
      setSessionsLoading(false);
    }
  };

  // Form validation
  const validateStep = (step: number): boolean => {
    const newErrors: Record<string, string> = {};

    switch (step) {
      case 1: // Basic Info
        if (!formData.name.trim()) {
          newErrors.name = 'Campaign name is required';
        }
        if (!formData.waha_session_id) {
          newErrors.waha_session_id = 'Please select a WhatsApp session';
        }
        break;

      case 2: // Messages
        if (formData.messages.length === 0 || !formData.messages[0].text.trim()) {
          newErrors.messages = 'At least one message is required';
        }
        if (formData.messages.length > 3) {
          newErrors.messages = 'Maximum 3 messages allowed';
        }
        break;

      case 3: // Audience
        if (formData.audience_type === 'csv_upload' && !formData.csv_file) {
          newErrors.csv_file = 'Please upload a CSV file';
        }
        if (formData.audience_type === 'tag_based' && formData.tag_filters?.selected_tags.length === 0) {
          newErrors.tags = 'Please select at least one tag';
        }
        break;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async () => {
    if (!validateStep(3)) return;

    setLoading(true);
    try {
      const campaignRequest: CampaignCreateRequest = {
        name: formData.name,
        waha_session_id: formData.waha_session_id,
        sending_speed: formData.sending_speed,
        schedule_type: formData.schedule_type,
        scheduled_time: formData.scheduled_time?.toISOString(),
        messages: formData.messages
          .filter(msg => msg.text.trim())
          .map((msg, index) => ({
            text: msg.text,
            media_url: msg.media_url || undefined,
            order: index + 1,
          })),
        audience_criteria: {
          filter_type: formData.audience_type,
          csv_data: formData.audience_type === 'csv_upload' ? [] : undefined, // Would be processed from CSV
          tag_filters: formData.audience_type === 'tag_based' ? {
            logic: formData.tag_filters?.logic || 'AND',
            tags: formData.tag_filters?.selected_tags || [],
          } : undefined,
        },
      };

      await onSubmit(campaignRequest);
    } catch (error) {
      console.error('Failed to create campaign:', error);
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
    setCurrentStep(prev => Math.max(prev - 1, 1));
  };

  // Render WAHA session selector
  const renderSessionSelector = () => {
    if (sessionsLoading) {
      return (
        <div className="animate-pulse">
          <div className="h-10 bg-gray-200 rounded"></div>
        </div>
      );
    }

    if (sessions.length === 0) {
      return (
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-yellow-800">
            No active WhatsApp sessions available. Please ensure WAHA is running and at least one session is active.
          </p>
          <button
            onClick={loadSessions}
            className="mt-2 px-3 py-1 bg-yellow-600 text-white rounded text-sm hover:bg-yellow-700"
          >
            Refresh Sessions
          </button>
        </div>
      );
    }

    return (
      <div>
        <select
          name="waha_session_id"
          value={formData.waha_session_id}
          onChange={(e) => setFormData(prev => ({ ...prev, waha_session_id: e.target.value }))}
          className={`w-full px-3 py-2 border rounded-md ${errors.waha_session_id ? 'border-red-300' : 'border-gray-300'}`}
          required
        >
          <option value="">Select WhatsApp Session</option>
          {sessions.map((session) => (
            <option key={session.id} value={session.id}>
              {wahaSessionService.formatSessionForDisplay(session)}
            </option>
          ))}
        </select>

        {/* Session info display */}
        {formData.waha_session_id && (
          <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded" data-testid="session-info">
            {(() => {
              const selectedSession = sessions.find(s => s.id === formData.waha_session_id);
              if (!selectedSession) return null;

              return (
                <div className="text-sm">
                  <p className="font-medium text-green-800">{selectedSession.name}</p>
                  <p className="text-green-600">
                    Business: {selectedSession.me.pushName} • Phone: {selectedSession.me.id}
                  </p>
                  <p className="text-green-600">
                    Status: {selectedSession.status} • Last updated: {new Date(selectedSession.last_updated).toLocaleString()}
                  </p>
                </div>
              );
            })()}
          </div>
        )}

        {errors.waha_session_id && (
          <p className="mt-1 text-sm text-red-600" data-testid="session-error">
            {errors.waha_session_id}
          </p>
        )}
      </div>
    );
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
          <span>Basic Info</span>
          <span>Messages</span>
          <span>Audience</span>
          <span>Review</span>
        </div>
      </div>

      <form onSubmit={(e) => e.preventDefault()}>
        {/* Step 1: Basic Information */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-gray-900">Campaign Details</h2>

            {/* Campaign Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Campaign Name *
              </label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className={`w-full px-3 py-2 border rounded-md ${errors.name ? 'border-red-300' : 'border-gray-300'}`}
                placeholder="Enter campaign name"
                required
              />
              {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name}</p>}
            </div>

            {/* WAHA Session Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                WhatsApp Session *
              </label>
              {renderSessionSelector()}
              <p className="mt-1 text-xs text-gray-500">
                Select the WhatsApp Business account to send from. Only active sessions are shown.
              </p>
            </div>

            {/* Sending Speed */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sending Speed
              </label>
              <select
                value={formData.sending_speed}
                onChange={(e) => setFormData(prev => ({ ...prev, sending_speed: e.target.value as any }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="slow">Slow (Conservative)</option>
                <option value="medium">Medium (Recommended)</option>
                <option value="fast">Fast (Aggressive)</option>
              </select>
            </div>

            {/* Schedule Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Schedule
              </label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="schedule_type"
                    value="immediate"
                    checked={formData.schedule_type === 'immediate'}
                    onChange={(e) => setFormData(prev => ({ ...prev, schedule_type: e.target.value as any }))}
                    className="mr-2"
                  />
                  Send immediately
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="schedule_type"
                    value="scheduled"
                    checked={formData.schedule_type === 'scheduled'}
                    onChange={(e) => setFormData(prev => ({ ...prev, schedule_type: e.target.value as any }))}
                    className="mr-2"
                  />
                  Schedule for later
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
            <h2 className="text-xl font-semibold text-gray-900">Campaign Messages</h2>
            <p className="text-sm text-gray-600">Add up to 3 messages for your campaign</p>

            {formData.messages.map((message, index) => (
              <div key={index} className="p-4 border border-gray-200 rounded-lg">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="font-medium">Message {index + 1}</h3>
                  {formData.messages.length > 1 && (
                    <button
                      type="button"
                      onClick={() => {
                        const newMessages = formData.messages.filter((_, i) => i !== index);
                        setFormData(prev => ({ ...prev, messages: newMessages }));
                      }}
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Remove
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
                  placeholder="Enter your message text..."
                  required={index === 0}
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
                  placeholder="Media URL (optional)"
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
                + Add Another Message
              </button>
            )}

            {errors.messages && <p className="text-sm text-red-600">{errors.messages}</p>}
          </div>
        )}

        {/* Step 3: Audience */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-gray-900">Target Audience</h2>

            <div className="space-y-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="audience_type"
                  value="all_contacts"
                  checked={formData.audience_type === 'all_contacts'}
                  onChange={(e) => setFormData(prev => ({ ...prev, audience_type: e.target.value as any }))}
                  className="mr-2"
                />
                All contacts
              </label>

              <label className="flex items-center">
                <input
                  type="radio"
                  name="audience_type"
                  value="csv_upload"
                  checked={formData.audience_type === 'csv_upload'}
                  onChange={(e) => setFormData(prev => ({ ...prev, audience_type: e.target.value as any }))}
                  className="mr-2"
                />
                Upload CSV file
              </label>

              <label className="flex items-center">
                <input
                  type="radio"
                  name="audience_type"
                  value="tag_based"
                  checked={formData.audience_type === 'tag_based'}
                  onChange={(e) => setFormData(prev => ({ ...prev, audience_type: e.target.value as any }))}
                  className="mr-2"
                />
                Filter by tags
              </label>
            </div>

            {formData.audience_type === 'csv_upload' && (
              <div>
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => setFormData(prev => ({ ...prev, csv_file: e.target.files?.[0] }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
                {errors.csv_file && <p className="mt-1 text-sm text-red-600">{errors.csv_file}</p>}
              </div>
            )}
          </div>
        )}

        {/* Step 4: Review */}
        {currentStep === 4 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-gray-900">Review Campaign</h2>

            <div className="bg-gray-50 p-4 rounded-lg space-y-3">
              <div>
                <span className="font-medium">Campaign:</span> {formData.name}
              </div>
              <div>
                <span className="font-medium">Session:</span> {
                  sessions.find(s => s.id === formData.waha_session_id)?.name || 'Unknown'
                }
              </div>
              <div>
                <span className="font-medium">Messages:</span> {formData.messages.filter(m => m.text.trim()).length}
              </div>
              <div>
                <span className="font-medium">Audience:</span> {formData.audience_type.replace('_', ' ')}
              </div>
              <div>
                <span className="font-medium">Schedule:</span> {formData.schedule_type}
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
                Previous
              </button>
            )}
          </div>

          <div className="space-x-3">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>

            {currentStep < 4 ? (
              <button
                type="button"
                onClick={nextStep}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Next
              </button>
            ) : (
              <button
                type="submit"
                onClick={handleSubmit}
                disabled={loading}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Create Campaign'}
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  );
};

export default CampaignWizard;