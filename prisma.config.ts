// Prisma 7 configuration — schema location, migrations folder and the
// database connection used by the CLI (migrate, studio, db push).
// The connection URL comes from .env (DATABASE_URL).
import 'dotenv/config'
import { defineConfig } from 'prisma/config'

export default defineConfig({
  schema: 'schema/schema.prisma',
  migrations: {
    path: 'schema/migrations',
  },
  datasource: {
    url: process.env.DATABASE_URL!,
  },
})
