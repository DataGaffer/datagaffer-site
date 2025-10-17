exports.config = { rawBody: true };

export async function handler(event) {
  console.log("🧩 typeof event.body:", typeof event.body);
  console.log("🧩 event.body length:", event.body?.length || 0);
  console.log("🧩 First 200 chars of body:", event.body?.slice?.(0, 200));

  return {
    statusCode: 200,
    body: "ok"
  };
}