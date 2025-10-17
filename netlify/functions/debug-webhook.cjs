// netlify/functions/debug-webhook.cjs
exports.config = { rawBody: true };

exports.handler = async (event) => {
  console.log("🔍 HEADERS:", JSON.stringify(event.headers, null, 2));
  console.log("🔍 BODY TYPE:", typeof event.body);
  console.log("🔍 BODY PREVIEW:", event.body?.slice?.(0, 300));

  return {
    statusCode: 200,
    body: JSON.stringify({
      message: "✅ Webhook test received",
      bodyType: typeof event.body,
      bodyPreview: event.body?.slice?.(0, 300),
    }),
  };
};