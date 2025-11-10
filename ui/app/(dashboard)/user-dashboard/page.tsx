'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Loader2, 
  Shield, 
  BarChart3, 
  FileText, 
  Settings,
  Download,
  Play,
  AlertTriangle,
  CheckCircle,
  Clock
} from 'lucide-react';
import { useToast } from '@/components/ui/toast/use-toast';

interface UserInfo {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  tenant_name: string;
  department: string;
  job_title: string;
}

interface ScanResult {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  findings_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
}

interface ComplianceReport {
  id: string;
  name: string;
  framework: string;
  status: 'generating' | 'completed' | 'failed';
  created_at: string;
  completed_at?: string;
  score: number;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
}

export default function UserDashboard() {
  const router = useRouter();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(true);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [scans, setScans] = useState<ScanResult[]>([]);
  const [reports, setReports] = useState<ComplianceReport[]>([]);
  const [isRunningScan, setIsRunningScan] = useState(false);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      
      // Load user info
      const userResponse = await fetch('/api/v1/users/me');
      if (userResponse.ok) {
        const userData = await userResponse.json();
        setUserInfo(userData);
      }

      // Load scans
      const scansResponse = await fetch('/api/v1/scans');
      if (scansResponse.ok) {
        const scansData = await scansResponse.json();
        setScans(scansData.scans || []);
      }

      // Load reports
      const reportsResponse = await fetch('/api/v1/reports');
      if (reportsResponse.ok) {
        const reportsData = await reportsResponse.json();
        setReports(reportsData.reports || []);
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunScan = async () => {
    setIsRunningScan(true);
    try {
      const response = await fetch('/api/v1/scans', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: `Security Scan - ${new Date().toLocaleDateString()}`,
          scan_type: 'full_scan'
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to start scan');
      }

      toast({
        title: 'Scan Started',
        description: 'Security scan has been initiated successfully.',
      });

      // Refresh scans list
      await loadDashboardData();
    } catch (err) {
      toast({
        title: 'Scan Failed',
        description: err instanceof Error ? err.message : 'Failed to start scan',
        variant: 'destructive',
      });
    } finally {
      setIsRunningScan(false);
    }
  };

  const handleDownloadReport = async (reportId: string) => {
    try {
      const response = await fetch(`/api/v1/reports/${reportId}/download`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `compliance-report-${reportId}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        toast({
          title: 'Report Downloaded',
          description: 'Compliance report has been downloaded successfully.',
        });
      }
    } catch (err) {
      toast({
        title: 'Download Failed',
        description: 'Failed to download the report',
        variant: 'destructive',
      });
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="default"><CheckCircle className="w-3 h-3 mr-1" />Completed</Badge>;
      case 'running':
        return <Badge variant="secondary"><Clock className="w-3 h-3 mr-1" />Running</Badge>;
      case 'failed':
        return <Badge variant="destructive"><AlertTriangle className="w-3 h-3 mr-1" />Failed</Badge>;
      case 'generating':
        return <Badge variant="secondary"><Clock className="w-3 h-3 mr-1" />Generating</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-600';
      case 'high':
        return 'text-orange-600';
      case 'medium':
        return 'text-yellow-600';
      case 'low':
        return 'text-blue-600';
      default:
        return 'text-gray-600';
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <Shield className="h-8 w-8 text-blue-600" />
              <div className="ml-3">
                <h1 className="text-2xl font-bold text-gray-900">
                  Welcome, {userInfo?.first_name}!
                </h1>
                <p className="text-sm text-gray-500">
                  {userInfo?.tenant_name} • {userInfo?.role?.charAt(0).toUpperCase() + userInfo?.role?.slice(1)}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Button
                variant="outline"
                onClick={() => router.push('/api/auth/logout')}
              >
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="scans">Security Scans</TabsTrigger>
            <TabsTrigger value="reports">Compliance Reports</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {/* Quick Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Scans</CardTitle>
                  <BarChart3 className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{scans.length}</div>
                  <p className="text-xs text-muted-foreground">
                    {scans.filter(s => s.status === 'completed').length} completed
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Critical Issues</CardTitle>
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-red-600">
                    {scans.reduce((sum, scan) => sum + scan.critical_count, 0)}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Require immediate attention
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Compliance Score</CardTitle>
                  <CheckCircle className="h-4 w-4 text-green-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {reports.length > 0 ? Math.round(reports[0].score) : 0}%
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Latest report
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Reports</CardTitle>
                  <FileText className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{reports.length}</div>
                  <p className="text-xs text-muted-foreground">
                    Generated reports
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
                <CardDescription>
                  Common tasks you can perform
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex space-x-4">
                  <Button
                    onClick={handleRunScan}
                    disabled={isRunningScan}
                  >
                    {isRunningScan ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    Run Security Scan
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => router.push('/dashboard/reports')}
                  >
                    <FileText className="mr-2 h-4 w-4" />
                    View Reports
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Recent Activity */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
                <CardDescription>
                  Your latest scans and reports
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {scans.slice(0, 3).map((scan) => (
                    <div key={scan.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <BarChart3 className="h-5 w-5 text-blue-600" />
                        <div>
                          <p className="font-medium">{scan.name}</p>
                          <p className="text-sm text-gray-500">
                            Started {new Date(scan.started_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {getStatusBadge(scan.status)}
                        {scan.status === 'completed' && (
                          <span className="text-sm text-gray-500">
                            {scan.findings_count} findings
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                  {scans.length === 0 && (
                    <div className="text-center py-8 text-gray-500">
                      No scans yet. Run your first security scan to get started.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Security Scans Tab */}
          <TabsContent value="scans" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Security Scans</CardTitle>
                <CardDescription>
                  Monitor your cloud infrastructure security
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {scans.length === 0 ? (
                    <div className="text-center py-8">
                      <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-medium text-gray-900 mb-2">No Scans Yet</h3>
                      <p className="text-gray-500 mb-4">
                        Run your first security scan to start monitoring your infrastructure.
                      </p>
                      <Button onClick={handleRunScan} disabled={isRunningScan}>
                        {isRunningScan ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <Play className="mr-2 h-4 w-4" />
                        )}
                        Run Security Scan
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {scans.map((scan) => (
                        <div key={scan.id} className="border rounded-lg p-4">
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="font-medium">{scan.name}</h3>
                            {getStatusBadge(scan.status)}
                          </div>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                            <div className="text-center">
                              <div className={`text-lg font-bold ${getSeverityColor('critical')}`}>
                                {scan.critical_count}
                              </div>
                              <div className="text-xs text-gray-500">Critical</div>
                            </div>
                            <div className="text-center">
                              <div className={`text-lg font-bold ${getSeverityColor('high')}`}>
                                {scan.high_count}
                              </div>
                              <div className="text-xs text-gray-500">High</div>
                            </div>
                            <div className="text-center">
                              <div className={`text-lg font-bold ${getSeverityColor('medium')}`}>
                                {scan.medium_count}
                              </div>
                              <div className="text-xs text-gray-500">Medium</div>
                            </div>
                            <div className="text-center">
                              <div className={`text-lg font-bold ${getSeverityColor('low')}`}>
                                {scan.low_count}
                              </div>
                              <div className="text-xs text-gray-500">Low</div>
                            </div>
                          </div>
                          <div className="flex justify-between items-center text-sm text-gray-500">
                            <span>Started: {new Date(scan.started_at).toLocaleString()}</span>
                            {scan.completed_at && (
                              <span>Completed: {new Date(scan.completed_at).toLocaleString()}</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Compliance Reports Tab */}
          <TabsContent value="reports" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Compliance Reports</CardTitle>
                <CardDescription>
                  View and download compliance reports
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {reports.length === 0 ? (
                    <div className="text-center py-8">
                      <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-medium text-gray-900 mb-2">No Reports Yet</h3>
                      <p className="text-gray-500">
                        Compliance reports will appear here once generated.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {reports.map((report) => (
                        <div key={report.id} className="border rounded-lg p-4">
                          <div className="flex items-center justify-between mb-3">
                            <div>
                              <h3 className="font-medium">{report.name}</h3>
                              <p className="text-sm text-gray-500">{report.framework}</p>
                            </div>
                            <div className="flex items-center space-x-2">
                              {getStatusBadge(report.status)}
                              {report.status === 'completed' && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleDownloadReport(report.id)}
                                >
                                  <Download className="mr-1 h-3 w-3" />
                                  Download
                                </Button>
                              )}
                            </div>
                          </div>
                          <div className="grid grid-cols-3 gap-4 mb-3">
                            <div className="text-center">
                              <div className="text-lg font-bold text-green-600">
                                {report.passed_checks}
                              </div>
                              <div className="text-xs text-gray-500">Passed</div>
                            </div>
                            <div className="text-center">
                              <div className="text-lg font-bold text-red-600">
                                {report.failed_checks}
                              </div>
                              <div className="text-xs text-gray-500">Failed</div>
                            </div>
                            <div className="text-center">
                              <div className="text-lg font-bold">
                                {Math.round(report.score)}%
                              </div>
                              <div className="text-xs text-gray-500">Score</div>
                            </div>
                          </div>
                          <div className="text-sm text-gray-500">
                            Created: {new Date(report.created_at).toLocaleString()}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
