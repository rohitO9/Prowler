import { NextRequest, NextResponse } from "next/server";
import { getUserPermissions } from "@/actions/admin/admin-user-management";

// Get User Permissions
export async function GET(
  request: NextRequest,
  { params }: { params: { userId: string } }
) {
  try {
    const { userId } = params;
    const result = await getUserPermissions(userId);
    
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
