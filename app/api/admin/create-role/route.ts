import { NextRequest, NextResponse } from "next/server";
import { createRole } from "@/actions/admin/admin-user-management";

// Create Role
export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const result = await createRole(formData);
    
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
