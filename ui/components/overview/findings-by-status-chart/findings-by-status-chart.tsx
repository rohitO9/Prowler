"use client";

import { Card, CardBody } from "@nextui-org/react";
import { Chip } from "@nextui-org/react";
import { TrendingUp } from "lucide-react";
import Link from "next/link";
import React, { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LabelList,
  ResponsiveContainer,
  Cell,
} from "recharts";

import { NotificationIcon, SuccessIcon } from "@/components/icons";

interface FindingsByStatusChartProps {
  findingsByStatus: {
    data: {
      attributes: {
        fail: number;
        pass: number;
        pass_new: number;
        fail_new: number;
        total: number;
      };
    };
  };
}

export const FindingsByStatusChart: React.FC<FindingsByStatusChartProps> = ({ findingsByStatus }) => {
  const { fail = 0, pass = 0, pass_new = 0, fail_new = 0 } = findingsByStatus?.data?.attributes || {};

  const data = [
    { status: "PASS", count: pass },
    { status: "FAIL", count: fail },
  ];

  const total = pass + fail;

  return (
    <Card className="h-full dark:bg-prowler-blue-400">
      <CardBody>
        <div className="flex flex-col items-center gap-6">
          <div className="w-full flex justify-center">
            <ResponsiveContainer width={300} height={250}>
              <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                <defs>
                  <linearGradient id="pass-gradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4ade80" />
                    <stop offset="100%" stopColor="#16a34a" />
                  </linearGradient>
                  <linearGradient id="fail-gradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f87171" />
                    <stop offset="100%" stopColor="#b91c1c" />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="status" tick={{ fontWeight: 'bold', fontSize: 16 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 14 }} domain={[0, 100]}>
                  <text
                    x={0}
                    y={0}
                    dx={-30}
                    dy={100}
                    textAnchor="middle"
                    transform="rotate(-90)"
                    style={{ fontSize: 14, fontWeight: 'bold' }}
                  >
                    Number of Findings
                  </text>
                </YAxis>
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div style={{ background: "#222", color: "#fff", padding: "8px 12px", borderRadius: 6 }}>
                          <strong>{label}</strong>
                          <div>{payload[0].value} findings</div>
                          <div style={{ fontSize: 12, marginTop: 4 }}>total {total}</div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="count" radius={[8, 8, 0, 0]} isAnimationActive={true}>
                  <Cell fill="url(#pass-gradient)" />
                  <Cell fill="url(#fail-gradient)" />
                  <LabelList
                    dataKey="count"
                    position="insideTop"
                    content={({ x = 0, y = 0, width = 0, value }) => (
                      <text
                        x={Number(x) + Number(width) / 2}
                        y={Number(y) + 20}
                        fill="#fff"
                        textAnchor="middle"
                        fontWeight="bold"
                        fontSize={16}
                      >
                        <tspan x={Number(x) + Number(width) / 2} dy="0">{value}</tspan>
                        <tspan x={Number(x) + Number(width) / 2} dy="18" fontSize={16}>findings</tspan>
                      </text>
                    )}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-2">
              <div className="flex items-center space-x-2">
                <Link
                  href="/findings?filter[status]=PASS"
                  className="flex items-center space-x-2"
                >
                  <Chip
                    className="h-5"
                    variant="flat"
                    startContent={<SuccessIcon size={18} />}
                    color="success"
                    radius="lg"
                    size="md"
                  >
                    {pass}
                  </Chip>
                </Link>
              </div>
              <div className="text-muted-foreground flex items-center gap-1 text-xs font-medium leading-none">
                {pass_new > 0 ? (
                  <>
                    +{pass_new} pass findings from last day{" "}
                    <TrendingUp className="h-4 w-4" />
                  </>
                ) : pass_new < 0 ? (
                  <>{pass_new} pass findings from last day</>
                ) : (
                  "No change from last day"
                )}
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <div className="flex items-center align-middle">
                <Link
                  href="/findings?filter[status]=FAIL"
                  className="flex items-center space-x-2"
                >
                  <Chip
                    className="h-5"
                    variant="flat"
                    startContent={<NotificationIcon size={18} />}
                    color="danger"
                    radius="lg"
                    size="md"
                  >
                    {fail}
                  </Chip>
                </Link>
              </div>
              <div className="text-muted-foreground flex items-center gap-1 text-xs font-medium leading-none">
                +{fail_new} fail findings from last day{" "}
                <TrendingUp className="h-4 w-4" />
              </div>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};
