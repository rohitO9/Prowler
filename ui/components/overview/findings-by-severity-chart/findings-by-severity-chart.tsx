"use client";

import { Card, CardBody } from "@nextui-org/react";
import { Pie, PieChart, Cell, Tooltip, Label } from "recharts";

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart/Chart";
import { FindingsSeverityOverview } from "@/types/components";

export interface ChartConfig {
  [key: string]: {
    label?: React.ReactNode;
    icon?: React.ComponentType<object>;
    color?: string;
    theme?: string;
    link?: string;
  };
}

const chartConfig = {
  critical: {
    label: "Critical",
    color: "hsl(var(--chart-critical))",
    link: "/findings?filter%5Bseverity__in%5D=critical",
  },
  high: {
    label: "High",
    color: "hsl(var(--chart-fail))",
    link: "/findings?filter%5Bseverity__in%5D=high",
  },
  medium: {
    label: "Medium",
    color: "hsl(var(--chart-medium))",
    link: "/findings?filter%5Bseverity__in%5D=medium",
  },
  low: {
    label: "Low",
    color: "hsl(var(--chart-low))",
    link: "/findings?filter%5Bseverity__in%5D=low",
  },
  informational: {
    label: "Informational",
    color: "hsl(var(--chart-informational))",
    link: "/findings?filter%5Bseverity__in%5D=informational",
  },
} satisfies ChartConfig;

const severities = ["critical", "high", "medium", "low", "informational"] as const;

export const FindingsBySeverityChart = ({
  findingsBySeverity,
}: {
  findingsBySeverity?: FindingsSeverityOverview;
}) => {
  const attributes = findingsBySeverity?.data?.attributes;
  if (!attributes) return null; // or show an empty state

  const chartData = Object.entries(attributes).map(([severity, findings]) => ({
    severity,
    findings,
    fill: chartConfig[severity as keyof typeof chartConfig]?.color,
    link: chartConfig[severity as keyof typeof chartConfig]?.link,
    label: chartConfig[severity as keyof typeof chartConfig]?.label,
  }));

  // Calculate total findings for center label and percentages
  const totalFindings = chartData.reduce((sum, d) => sum + d.findings, 0);

  // Legend for severity colors (below chart, using gradients)
  const Legend = () => (
    <div className="flex flex-wrap justify-center gap-6 mt-4">
      {gradients.map((g, idx) => (
        <div key={g.id} className="flex items-center gap-2 text-sm font-semibold">
          <span style={{
            background: `linear-gradient(90deg, ${g.from} 0%, ${g.to} 100%)`,
            width: 16,
            height: 16,
            borderRadius: 3,
            display: 'inline-block',
          }} />
          <span>{chartConfig[severities[idx]].label}</span>
        </div>
      ))}
    </div>
  );

  // Improved tooltip for stability and clarity
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const percent = totalFindings > 0 ? ((data.findings / totalFindings) * 100).toFixed(1) : 0;
      return (
        <div style={{
          background: 'rgba(30,41,59,0.95)',
          color: '#fff',
          borderRadius: 6,
          padding: '8px 12px',
          fontSize: 13,
          minWidth: 80,
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
        }}>
          <div style={{ fontWeight: 600 }}>{data.label}</div>
          <div>{data.findings} findings</div>
          <div>{percent}%</div>
        </div>
      );
    }
    return null;
  };

  // Large, bold findings count label inside each slice
  const renderCustomizedLabel = (props: any) => {
    const { cx, cy, midAngle, innerRadius, outerRadius, findings } = props;
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.6;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    return (
      <text x={x} y={y} fill="#333" textAnchor="middle" dominantBaseline="central" fontSize={16} fontWeight="bold">
        {findings > 0 ? findings : ""}
      </text>
    );
  };

  // Light color palette for chart slices (theme-related)
  const chartSliceColors: Record<string, string> = {
    critical: '#F472B6',      // light pink
    high: '#FB7185',          // light red
    medium: '#FDBA74',        // light orange
    low: '#FDE68A',           // light yellow
    informational: '#E0E7EF', // light blue/gray
  };

  // Legend color palette (distinct from chart colors)
  const legendColors: Record<string, string> = {
    critical: '#8B1E5A',
    high: '#E11D48',
    medium: '#F97316',
    low: '#FACC15',
    informational: '#F1F5F9',
  };

  // Gradient definitions for each severity
  const gradients = [
    {
      id: 'critical-gradient',
      from: '#F472B6',
      to: '#BE185D',
    },
    {
      id: 'high-gradient',
      from: '#FB7185',
      to: '#BE123C',
    },
    {
      id: 'medium-gradient',
      from: '#FDBA74',
      to: '#EA580C',
    },
    {
      id: 'low-gradient',
      from: '#FDE68A',
      to: '#CA8A04',
    },
    {
      id: 'informational-gradient',
      from: '#E0E7EF',
      to: '#64748B',
    },
  ];
  const gradientMap: Record<string, string> = {
    critical: 'url(#critical-gradient)',
    high: 'url(#high-gradient)',
    medium: 'url(#medium-gradient)',
    low: 'url(#low-gradient)',
    informational: 'url(#informational-gradient)',
  };

  return (
    <Card className="h-full dark:bg-prowler-blue-400">
      <CardBody>
        <div className="flex flex-col items-center justify-center">
          <ChartContainer config={chartConfig} className="aspect-square w-[260px] min-w-[200px]">
            <PieChart width={260} height={260}>
              <defs>
                {gradients.map((g) => (
                  <linearGradient key={g.id} id={g.id} x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor={g.from} />
                    <stop offset="100%" stopColor={g.to} />
                  </linearGradient>
                ))}
              </defs>
              <Tooltip content={<CustomTooltip />} />
              <Pie
                data={chartData}
                dataKey="findings"
                nameKey="label"
                cx="50%"
                cy="50%"
                outerRadius={100}
                paddingAngle={2}
                cornerRadius={6}
                label={renderCustomizedLabel}
                labelLine={false}
                onClick={(_, idx) => {
                  const link = chartData[idx]?.link;
                  if (link) window.location.href = link;
                }}
                style={{ cursor: "pointer" }}
              >
                {chartData.map((entry, idx) => (
                  <Cell key={`cell-${idx}`} fill={gradientMap[entry.severity]} />
                ))}
              </Pie>
            </PieChart>
          </ChartContainer>
          <Legend />
        </div>
      </CardBody>
    </Card>
  );
};
