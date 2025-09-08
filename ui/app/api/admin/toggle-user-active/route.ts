import { NextRequest, NextResponse } from "next/server";
import { toggleUserActive } from "@/actions/admin/admin-user-management";

// Toggle User Active Status
export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const result = await toggleUserActive(formData);
    
    if (result.error) {
      return NextResponse.json({ error: result.error }, { status: 400 });
    }
    
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
