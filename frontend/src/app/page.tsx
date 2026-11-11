"use client";

import React, { useState, useEffect } from "react";
import { DatasetProfile, SampleDatasetInfo, AnalysisResponse, HealthStatus } from "@/types";
import { api } from "@/lib/api";
import { Navbar } from "@/components/Navbar";
import { LandingIngestion } from "@/components/LandingIngestion";
import { DatasetWorkspace } from "@/components/DatasetWorkspace";
import { AnalysisWorkspace } from "@/components/AnalysisWorkspace";
import { ReportModal } from "@/components/ReportModal";

export default function Home() {
  const [samples, setSamples] = useState<SampleDatasetInfo[]>([]);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [history, setHistory] = useState<AnalysisResponse[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [systemHealthy, setSystemHealthy] = useState(false);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [activeReportAnalysis, setActiveReportAnalysis] = useState<AnalysisResponse | null>(null);

  // Initialize and check health & samples
  useEffect(() => {
    async function init() {
      try {
        const health = await api.getHealth();
        setHealthStatus(health);
        if (health.status === "ok") {
          setSystemHealthy(true);
        }
      } catch (err) {
        console.warn("Backend not yet ready:", err);
      }

      try {
        const sampleList = await api.getSamples();
        setSamples(sampleList);
      } catch (err) {
        console.warn("Failed to load sample list:", err);
      }
    }

    init();
  }, []);

  const handleUpload = async (file: File) => {
    setIsProcessing(true);
    try {
      // 1. Upload & profile
      const newProfile = await api.uploadDataset(file);
      setProfile(newProfile);

      // 2. Create isolated session
      const session = await api.createSession(newProfile.dataset_id);
      setSessionId(session.session_id);
      setHistory([]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSelectSample = async (sampleId: string) => {
    setIsProcessing(true);
    try {
      // 1. Load sample dataset
      const newProfile = await api.loadSample(sampleId);
      setProfile(newProfile);

      // 2. Create isolated session
      const session = await api.createSession(newProfile.dataset_id);
      setSessionId(session.session_id);
      setHistory([]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setProfile(null);
    setSessionId(null);
    setHistory([]);
  };

  const handleNewAnalysis = (analysis: AnalysisResponse) => {
    setHistory((prev) => [analysis, ...prev]);
  };

  // Get current sample questions if applicable
  const currentSampleQuestions = profile?.dataset_id.startsWith("sample-")
    ? samples.find((s) => profile.dataset_id.includes(s.id))?.sample_questions || []
    : [];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-white">
      {/* Navigation Bar */}
      <Navbar
        datasetProfile={profile}
        onReset={handleReset}
        systemHealthy={systemHealthy}
        healthStatus={healthStatus}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {!profile || !sessionId ? (
          <LandingIngestion
            samples={samples}
            onUpload={handleUpload}
            onSelectSample={handleSelectSample}
            isProcessing={isProcessing}
          />
        ) : (
          <div className="space-y-8 animate-fadeIn">
            {/* Dataset Profiling and Schema Workspace */}
            <DatasetWorkspace profile={profile} />

            {/* AI Agent Analysis and Query Workspace */}
            <AnalysisWorkspace
              sessionId={sessionId}
              datasetProfile={profile}
              sampleQuestions={currentSampleQuestions}
              history={history}
              onNewAnalysis={handleNewAnalysis}
              onOpenReport={(analysis) => setActiveReportAnalysis(analysis)}
            />
          </div>
        )}
      </main>

      {/* Report Modal */}
      {activeReportAnalysis && (
        <ReportModal
          analysis={activeReportAnalysis}
          onClose={() => setActiveReportAnalysis(null)}
        />
      )}

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/60 py-6 text-center text-xs text-slate-500">
        <p>
          Data Detective &bull; AI Data Analyst &bull; Grounded in Sandboxed Python Execution &bull; Plotly Visualizations
        </p>
      </footer>
    </div>
  );
}
