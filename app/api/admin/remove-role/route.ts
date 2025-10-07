import { NextRequest, NextResponse } from "next/server";
import { removeRoleFromUser } from "@/actions/admin/admin-user-management";

// Remove Role from User
export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const result = await removeRoleFromUser(formData);
    
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
