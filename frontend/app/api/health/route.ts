export async function GET() {
  return Response.json({ online: true, service: "tripweaver-frontend" })
}
